package {{TEST_PACKAGE}};

import static com.tngtech.archunit.core.domain.JavaClass.Predicates.assignableTo;
import static com.tngtech.archunit.core.domain.properties.CanBeAnnotated.Predicates.metaAnnotatedWith;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.fields;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.methods;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noFields;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noMethods;
import static com.tngtech.archunit.library.GeneralCodingRules.NO_CLASSES_SHOULD_ACCESS_STANDARD_STREAMS;
import static com.tngtech.archunit.library.freeze.FreezingArchRule.freeze;

import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaMethod;
import com.tngtech.archunit.core.domain.JavaMethodCall;
import com.tngtech.archunit.core.domain.JavaModifier;
import com.tngtech.archunit.core.domain.JavaParameter;
import com.tngtech.archunit.core.domain.JavaType;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchCondition;
import com.tngtech.archunit.lang.ArchRule;
import com.tngtech.archunit.lang.ConditionEvents;
import com.tngtech.archunit.lang.SimpleConditionEvent;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * Mistakes that compile, pass most tests, and break at runtime or on the next upgrade. Each failure message says
 * how to fix it. On a codebase that baseline.py recorded, the violations it found in src/test/resources/archunit_store
 * are tolerated; new ones fail, and fixed ones drop out of the record. Without that record every violation fails.
 */
class CodeRulesTests {

    private static final String BASE_PACKAGE = "{{BASE_PACKAGE}}";

    private static final JavaClasses MAIN = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
            .importPackages(BASE_PACKAGE);

    private static final JavaClasses TESTS = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.ONLY_INCLUDE_TESTS)
            .importPackages(BASE_PACKAGE);

    private static final boolean RECORDED = Files.isDirectory(Path.of("src/test/resources/archunit_store"))
            || Boolean.getBoolean("archunit.freeze.store.default.allowStoreCreation");

    /** Spring applies these through a proxy, so a call from the same class skips them. */
    private static final List<String> APPLIED_BY_PROXY = List.of(
            "org.springframework.transaction.annotation.Transactional",
            "jakarta.transaction.Transactional",
            "org.springframework.scheduling.annotation.Async",
            "org.springframework.cache.annotation.Cacheable",
            "org.springframework.cache.annotation.CacheEvict",
            "org.springframework.cache.annotation.CachePut",
            "org.springframework.security.access.prepost.PreAuthorize",
            "org.springframework.security.access.prepost.PostAuthorize",
            "org.springframework.resilience.annotation.Retryable",
            "org.springframework.resilience.annotation.ConcurrencyLimit",
            "org.springframework.retry.annotation.Retryable");

    /**
     * On a class, these apply to each public method, so a call from the same class skips them too. A self-call in a
     * class-level @Transactional or secured class already runs inside the caller's transaction or check.
     */
    /** Each resilience annotation, and what switches it on besides @EnableResilientMethods. */
    private static final List<List<String>> RESILIENCE = List.of(
            List.of("org.springframework.resilience.annotation.Retryable",
                    "org.springframework.resilience.annotation.RetryAnnotationBeanPostProcessor"),
            List.of("org.springframework.resilience.annotation.ConcurrencyLimit",
                    "org.springframework.resilience.annotation.ConcurrencyLimitBeanPostProcessor"));

    private static final Map<String, Boolean> SWITCHED_ON = new ConcurrentHashMap<>();

    private static final List<String> LOOKED_UP_BY_ID = List.of(
            "org.springframework.web.bind.annotation.PathVariable",
            "org.springframework.web.bind.annotation.RequestParam");

    private static final List<String> APPLIED_BY_PROXY_ON_CLASS = APPLIED_BY_PROXY.stream()
            .filter(annotation -> !annotation.endsWith(".Transactional") && !annotation.contains(".prepost."))
            .toList();

    @Test
    void proxiedMethodsAreNotCalledFromTheirOwnClass() {
        frozenIfRecorded(classes()
                .should(notCallTheirOwnProxiedMethods())
                .because("the call skips the proxy, so the annotation does nothing. Move the method to another "
                        + "bean and inject it")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void controllersDontStartTransactions() {
        frozenIfRecorded(noMethods()
                .that()
                .areDeclaredInClassesThat(metaAnnotatedWith("org.springframework.stereotype.Controller"))
                .should()
                .beAnnotatedWith("org.springframework.transaction.annotation.Transactional")
                .orShould()
                .beAnnotatedWith("jakarta.transaction.Transactional")
                .because("transactions belong in the service the controller calls. Move @Transactional there")
                .allowEmptyShould(true))
                .check(MAIN);
        frozenIfRecorded(noClasses()
                .that(metaAnnotatedWith("org.springframework.stereotype.Controller"))
                .should()
                .beAnnotatedWith("org.springframework.transaction.annotation.Transactional")
                .orShould()
                .beAnnotatedWith("jakarta.transaction.Transactional")
                .because("on a class, it makes every endpoint transactional. Move @Transactional to the service "
                        + "the controller calls")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void controllersDontUseRepositories() {
        frozenIfRecorded(noClasses()
                .that(metaAnnotatedWith("org.springframework.stereotype.Controller"))
                .should()
                .dependOnClassesThat()
                .areAssignableTo("org.springframework.data.repository.Repository")
                .because("business rules and transactions live in services. Call a service instead")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void controllersDontExposeEntities() {
        frozenIfRecorded(methods()
                .that()
                .areMetaAnnotatedWith("org.springframework.web.bind.annotation.RequestMapping")
                .should(notTakeOrReturnEntities())
                .because("an entity in the API exposes every column, lets a request set any of them, ties the API to "
                        + "the schema, and fails on lazy associations. Take and return a record, and map it in the "
                        + "service")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void manyToManyAssociationsAreSets() {
        frozenIfRecorded(fields()
                .that()
                .areAnnotatedWith("jakarta.persistence.ManyToMany")
                .should()
                .haveRawType(assignableTo(Set.class))
                .because("with a List, removing one element deletes every join row of the owner and inserts the "
                        + "others again. Use a Set, such as a LinkedHashSet to keep the order")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void resilienceAnnotationsAreSwitchedOn() {
        frozenIfRecorded(classes()
                .should(beSwitchedOnIfTheyUseResilienceAnnotations())
                .because("@Retryable and @ConcurrencyLimit do nothing until @EnableResilientMethods is on a "
                        + "@Configuration class. Add it")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void dependenciesAreInjectedThroughConstructors() {
        frozenIfRecorded(noFields()
                .should()
                .beAnnotatedWith("org.springframework.beans.factory.annotation.Autowired")
                .because("a final field set in the constructor can't be null and works in plain unit tests. "
                        + "Take the dependency as a constructor parameter")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void codeLogsInsteadOfPrinting() {
        frozenIfRecorded(NO_CLASSES_SHOULD_ACCESS_STANDARD_STREAMS
                .because("output on System.out or System.err skips log levels and structured logging. Use an "
                        + "org.slf4j.Logger")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void jsonUsesJackson3() {
        frozenIfRecorded(noClasses()
                .should()
                .dependOnClassesThat()
                .resideInAnyPackage("com.fasterxml.jackson.databind..", "com.fasterxml.jackson.core..")
                .because("Spring Boot 4 configures Jackson 3 and ignores Jackson 2 customizers, serializers and "
                        + "ObjectMappers. Use tools.jackson.databind and tools.jackson.core; annotations stay in "
                        + "com.fasterxml.jackson.annotation")
                .allowEmptyShould(true))
                .check(new ClassFileImporter().importPackages(BASE_PACKAGE));
    }

    @Test
    void nullnessUsesJSpecify() {
        frozenIfRecorded(noClasses()
                .should()
                .dependOnClassesThat()
                .haveFullyQualifiedName("org.springframework.lang.Nullable")
                .orShould()
                .dependOnClassesThat()
                .haveFullyQualifiedName("org.springframework.lang.NonNull")
                .because("Spring Framework 7 deprecates its own nullness annotations and NullAway checks JSpecify's. "
                        + "Use org.jspecify.annotations.Nullable")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void testsUseJUnit5() {
        frozenIfRecorded(noClasses()
                .should()
                .dependOnClassesThat()
                .resideInAnyPackage("org.junit", "org.junit.runner..", "org.junit.rules..")
                .because("Spring Boot runs only JUnit Jupiter, so a JUnit 4 test is silently skipped. Use "
                        + "org.junit.jupiter.api and AssertJ")
                .allowEmptyShould(true))
                .check(TESTS);
    }

    @Test
    void testsAreNotDisabled() {
        frozenIfRecorded(noClasses()
                .should()
                .beAnnotatedWith("org.junit.jupiter.api.Disabled")
                .because("a disabled test keeps the build green while it checks nothing. Fix the test or delete it")
                .allowEmptyShould(true))
                .check(TESTS);
        frozenIfRecorded(noMethods()
                .should()
                .beAnnotatedWith("org.junit.jupiter.api.Disabled")
                .because("a disabled test keeps the build green while it checks nothing. Fix the test or delete it")
                .allowEmptyShould(true))
                .check(TESTS);
    }

    private static ArchRule frozenIfRecorded(ArchRule rule) {
        return RECORDED ? freeze(rule) : rule;
    }

    private static ArchCondition<JavaClass> notCallTheirOwnProxiedMethods() {
        return new ArchCondition<>(
                "not call their own @Transactional, @Async, @Cacheable, @Retryable or secured methods") {
            @Override
            public void check(JavaClass javaClass, ConditionEvents events) {
                for (JavaMethodCall call : javaClass.getMethodCallsFromSelf()) {
                    if (!call.getTargetOwner().equals(javaClass)) {
                        continue;
                    }
                    call.getTarget()
                            .resolveMember()
                            .flatMap(method -> skippedAnnotation(javaClass, method))
                            .ifPresent(annotation -> events.add(SimpleConditionEvent.violated(
                                    call,
                                    call.getDescription() + " skips the proxy, so @"
                                            + annotation.substring(annotation.lastIndexOf('.') + 1)
                                            + " does nothing")));
                }
            }
        };
    }

    /**
     * Looks through the return type and the bound parameters, and into the fields of this project's own types, so an
     * entity inside a record counts. A path variable or request parameter is looked up by its id, so it binds nothing.
     */
    private static ArchCondition<JavaMethod> notTakeOrReturnEntities() {
        return new ArchCondition<>("not take or return a JPA entity") {
            @Override
            public void check(JavaMethod method, ConditionEvents events) {
                Set<JavaClass> seen = new HashSet<>();
                Stream.concat(
                                Stream.of(method.getReturnType()),
                                method.getParameters().stream()
                                        .filter(parameter -> LOOKED_UP_BY_ID.stream()
                                                .noneMatch(parameter::isAnnotatedWith))
                                        .map(JavaParameter::getType))
                        .flatMap(type -> entitiesIn(type, seen))
                        .forEach(entity -> events.add(SimpleConditionEvent.violated(
                                method, method.getDescription() + " exposes the entity " + entity.getSimpleName())));
            }
        };
    }

    private static Stream<JavaClass> entitiesIn(JavaType type, Set<JavaClass> seen) {
        return type.getAllInvolvedRawTypes().stream().filter(seen::add).flatMap(raw -> {
            if (raw.isAnnotatedWith("jakarta.persistence.Entity")) {
                return Stream.of(raw);
            }
            if (!raw.getPackageName().startsWith(BASE_PACKAGE)) {
                return Stream.empty();
            }
            return raw.getFields().stream()
                    .filter(field -> !field.getModifiers().contains(JavaModifier.STATIC))
                    .flatMap(field -> entitiesIn(field.getType(), seen));
        });
    }

    private static ArchCondition<JavaClass> beSwitchedOnIfTheyUseResilienceAnnotations() {
        return new ArchCondition<>("have their resilience annotations switched on") {
            @Override
            public void check(JavaClass javaClass, ConditionEvents events) {
                if (javaClass.isAnnotation()) {
                    return;
                }
                for (List<String> annotation : RESILIENCE) {
                    String name = annotation.get(0);
                    boolean used = javaClass.isMetaAnnotatedWith(name)
                            || javaClass.getMethods().stream().anyMatch(method -> method.isMetaAnnotatedWith(name));
                    if (used && !SWITCHED_ON.computeIfAbsent(annotation.get(1), CodeRulesTests::switchedOn)) {
                        events.add(SimpleConditionEvent.violated(javaClass, javaClass.getName() + " uses @"
                                + name.substring(name.lastIndexOf('.') + 1) + ", but nothing switches it on"));
                    }
                }
            }
        };
    }

    private static boolean switchedOn(String postProcessor) {
        return MAIN.stream().anyMatch(javaClass -> javaClass.isMetaAnnotatedWith(
                        "org.springframework.resilience.annotation.EnableResilientMethods")
                || javaClass.getDirectDependenciesFromSelf().stream()
                        .anyMatch(dependency -> dependency.getTargetClass().getName().equals(postProcessor)));
    }

    private static Optional<String> skippedAnnotation(JavaClass owner, JavaMethod method) {
        return APPLIED_BY_PROXY.stream()
                .filter(method::isAnnotatedWith)
                .findFirst()
                .or(() -> method.getModifiers().contains(JavaModifier.PUBLIC)
                        ? APPLIED_BY_PROXY_ON_CLASS.stream().filter(owner::isAnnotatedWith).findFirst()
                        : Optional.empty());
    }
}
