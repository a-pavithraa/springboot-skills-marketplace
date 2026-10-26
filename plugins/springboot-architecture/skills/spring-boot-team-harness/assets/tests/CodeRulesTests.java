package {{TEST_PACKAGE}};

import static com.tngtech.archunit.base.DescribedPredicate.not;
import static com.tngtech.archunit.core.domain.JavaClass.Predicates.assignableTo;
import static com.tngtech.archunit.core.domain.properties.CanBeAnnotated.Predicates.metaAnnotatedWith;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.fields;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.members;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.methods;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noFields;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noMembers;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noMethods;
import static com.tngtech.archunit.library.GeneralCodingRules.NO_CLASSES_SHOULD_ACCESS_STANDARD_STREAMS;
import static com.tngtech.archunit.library.freeze.FreezingArchRule.freeze;

import com.tngtech.archunit.core.domain.JavaAnnotation;
import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaEnumConstant;
import com.tngtech.archunit.core.domain.JavaField;
import com.tngtech.archunit.core.domain.JavaMember;
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
import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Predicate;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * Mistakes that compile, pass most tests, and break at runtime or on the next upgrade. Each failure message says
 * how to fix it. On a codebase that baseline.py recorded, the violations it found in src/test/resources/archunit_store
 * are tolerated; new ones fail, and fixed ones drop out of the record. Without that record every violation fails, and
 * so does every violation of a rule added after baseline.py ran, until it runs again: ArchUnit would otherwise record
 * a new rule's violations on its first run, including the ones a change in progress just added.
 */
class CodeRulesTests {

    private static final String BASE_PACKAGE = "{{BASE_PACKAGE}}";

    private static final JavaClasses MAIN = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
            .importPackages(BASE_PACKAGE);

    private static final JavaClasses TESTS = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.ONLY_INCLUDE_TESTS)
            .importPackages(BASE_PACKAGE);

    private static final boolean RECORDING = Boolean.getBoolean("archunit.freeze.store.default.allowStoreCreation");

    private static final Set<String> RECORDED_RULES = recordedRules();

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
     * Each annotation that does nothing until something switches it on: the @Enable annotation, its bean post
     * processor registered by hand, or an auto-configuration that enables it when its class is on the classpath.
     */
    private record Switch(String annotation, String enabler, String postProcessor, List<String> autoConfigurations) {}

    private static final List<Switch> RESILIENCE = List.of(
            new Switch("org.springframework.resilience.annotation.Retryable",
                    "org.springframework.resilience.annotation.EnableResilientMethods",
                    "org.springframework.resilience.annotation.RetryAnnotationBeanPostProcessor", List.of()),
            new Switch("org.springframework.resilience.annotation.ConcurrencyLimit",
                    "org.springframework.resilience.annotation.EnableResilientMethods",
                    "org.springframework.resilience.annotation.ConcurrencyLimitBeanPostProcessor", List.of()));

    private static final List<Switch> ASYNC_AND_SCHEDULING = List.of(
            new Switch("org.springframework.scheduling.annotation.Async",
                    "org.springframework.scheduling.annotation.EnableAsync",
                    "org.springframework.scheduling.annotation.AsyncAnnotationBeanPostProcessor",
                    List.of("org.springframework.modulith.events.config.EventPublicationAutoConfiguration")),
            new Switch("org.springframework.scheduling.annotation.Scheduled",
                    "org.springframework.scheduling.annotation.EnableScheduling",
                    "org.springframework.scheduling.annotation.ScheduledAnnotationBeanPostProcessor", List.of()));

    private static final Map<Switch, Boolean> SWITCHED_ON = new ConcurrentHashMap<>();

    /** Calls on these talk to another system over the network. */
    private static final List<String> REMOTE_CLIENT_PACKAGES = List.of(
            "org.springframework.web.client", "org.springframework.web.reactive.function.client", "java.net.http");

    private static final List<String> TO_ONE = List.of("jakarta.persistence.ManyToOne", "jakarta.persistence.OneToOne");

    /** Each of these maps an enum column its own way, so @Enumerated doesn't apply. */
    private static final List<String> CONVERTED = List.of(
            "jakarta.persistence.Convert",
            "jakarta.persistence.Transient",
            "org.hibernate.annotations.JdbcTypeCode",
            "org.hibernate.annotations.JdbcType",
            "org.hibernate.annotations.Type");

    private static final List<String> LOOKED_UP_BY_ID = List.of(
            "org.springframework.web.bind.annotation.PathVariable",
            "org.springframework.web.bind.annotation.RequestParam");

    /**
     * On a class, these apply to each public method, so a call from the same class skips them too. A self-call in a
     * class-level @Transactional or secured class already runs inside the caller's transaction or check.
     */
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
                .should(haveTheirAnnotationsSwitchedOn("resilience annotations", RESILIENCE))
                .because("@Retryable and @ConcurrencyLimit do nothing until @EnableResilientMethods is on a "
                        + "@Configuration class. Add it")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void asyncAndSchedulingAreSwitchedOn() {
        frozenIfRecorded(classes()
                .should(haveTheirAnnotationsSwitchedOn("@Async and @Scheduled annotations", ASYNC_AND_SCHEDULING))
                .because("@Async runs the method on the caller's thread, and @Scheduled never runs it, until "
                        + "@EnableAsync or @EnableScheduling is on a @Configuration class. Add it")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void proxiedMethodsCanBeIntercepted() {
        frozenIfRecorded(methods()
                .should(beInterceptableIfProxied())
                .because("the proxy can't intercept a private, final or static method, so the annotation does "
                        + "nothing. Make the method public and not final, or move the annotation to one that is")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void httpClientsComeFromTheBuilder() {
        frozenIfRecorded(noClasses()
                .should()
                .callMethod("org.springframework.web.client.RestClient", "create")
                .orShould()
                .callMethod("org.springframework.web.client.RestClient", "create", "java.lang.String")
                .orShould()
                .callMethod("org.springframework.web.client.RestClient", "create", "java.net.URI")
                .orShould()
                .callMethod("org.springframework.web.reactive.function.client.WebClient", "create")
                .orShould()
                .callMethod("org.springframework.web.reactive.function.client.WebClient", "create", "java.lang.String")
                .orShould()
                .callConstructor("org.springframework.web.client.RestTemplate")
                .because("a client created this way has no connect or read timeout, so a slow server holds the "
                        + "caller's thread, and it skips Boot's metrics and tracing. Build it from the injected "
                        + "RestClient.Builder or WebClient.Builder, with timeouts in spring.http.clients.*")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void transactionsDontWaitOnRemoteCalls() {
        frozenIfRecorded(methods()
                .should(notCallRemoteClientsInsideATransaction())
                .because("the transaction holds a database connection for as long as the remote call takes, so a "
                        + "slow server drains the connection pool. Make the call before or after the transaction, "
                        + "in a method without @Transactional")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void toOneAssociationsAreLazy() {
        frozenIfRecorded(members()
                .should(beLazyIfToOne())
                .because("@ManyToOne and @OneToOne load the associated row with every query by default, one query "
                        + "per row for a list. Set fetch = FetchType.LAZY, and fetch the association in the query "
                        + "that needs it")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void enumColumnsAreStoredByName() {
        frozenIfRecorded(fields()
                .should(beStoredByNameIfPersistentEnums())
                .because("without @Enumerated(EnumType.STRING) the column holds the constant's position, so adding "
                        + "or reordering a constant changes what existing rows mean. Add @Enumerated(EnumType.STRING), "
                        + "with a migration that converts existing values")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void servicesDontUseHttpTypes() {
        frozenIfRecorded(noClasses()
                .that(metaAnnotatedWith("org.springframework.stereotype.Service"))
                .should()
                .dependOnClassesThat()
                .haveFullyQualifiedName("org.springframework.web.server.ResponseStatusException")
                .orShould()
                .dependOnClassesThat()
                .resideInAPackage("jakarta.servlet..")
                .because("the service then answers in HTTP terms, which breaks when a listener or a scheduled job "
                        + "calls it. Throw the project's own exception and map it to a status in the "
                        + "@RestControllerAdvice; pass request values in as parameters")
                .allowEmptyShould(true))
                .check(MAIN);
        frozenIfRecorded(noMethods()
                .that()
                .areDeclaredInClassesThat(metaAnnotatedWith("org.springframework.stereotype.Service"))
                .should()
                .haveRawReturnType("org.springframework.http.ResponseEntity")
                .because("status codes and headers belong to the controller. Return the result, and build the "
                        + "ResponseEntity in the controller")
                .allowEmptyShould(true))
                .check(MAIN);
    }

    @Test
    void oldCodeIsDeletedNotDeprecated() {
        frozenIfRecorded(noClasses()
                .should()
                .beAnnotatedWith(Deprecated.class)
                .because("nothing outside this repository calls it. Update every caller in this change and delete "
                        + "the old code. To retire an endpoint, deprecate the controller method")
                .allowEmptyShould(true))
                .check(MAIN);
        frozenIfRecorded(noMembers()
                .that()
                .areDeclaredInClassesThat(not(metaAnnotatedWith("org.springframework.stereotype.Controller")))
                .should()
                .beAnnotatedWith(Deprecated.class)
                .because("nothing outside this repository calls it. Update every caller in this change and delete "
                        + "the old code")
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
        return RECORDING || RECORDED_RULES.contains(rule.getDescription()) ? freeze(rule) : rule;
    }

    /** The store files each rule under its description, in this properties file. */
    private static Set<String> recordedRules() {
        Path index = Path.of("src/test/resources/archunit_store/stored.rules");
        if (!Files.isRegularFile(index)) {
            return Set.of();
        }
        Properties rules = new Properties();
        try (Reader reader = Files.newBufferedReader(index)) {
            rules.load(reader);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return rules.stringPropertyNames();
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
                                            + simpleName(annotation) + " does nothing")));
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

    private static ArchCondition<JavaClass> haveTheirAnnotationsSwitchedOn(String which, List<Switch> switches) {
        return new ArchCondition<>("have their " + which + " switched on") {
            @Override
            public void check(JavaClass javaClass, ConditionEvents events) {
                if (javaClass.isAnnotation()) {
                    return;
                }
                for (Switch candidate : switches) {
                    String name = candidate.annotation();
                    boolean used = javaClass.isMetaAnnotatedWith(name)
                            || javaClass.getMethods().stream().anyMatch(method -> method.isMetaAnnotatedWith(name));
                    if (used && !SWITCHED_ON.computeIfAbsent(candidate, CodeRulesTests::switchedOn)) {
                        events.add(SimpleConditionEvent.violated(javaClass, javaClass.getName() + " uses @"
                                + simpleName(name) + ", but nothing switches it on: add @"
                                + simpleName(candidate.enabler())));
                    }
                }
            }
        };
    }

    private static boolean switchedOn(Switch candidate) {
        return candidate.autoConfigurations().stream().anyMatch(CodeRulesTests::onClasspath)
                || MAIN.stream().anyMatch(javaClass -> javaClass.isMetaAnnotatedWith(candidate.enabler())
                        || javaClass.getDirectDependenciesFromSelf().stream().anyMatch(dependency ->
                                dependency.getTargetClass().getName().equals(candidate.postProcessor())));
    }

    private static boolean onClasspath(String className) {
        try {
            Class.forName(className, false, CodeRulesTests.class.getClassLoader());
            return true;
        } catch (ClassNotFoundException e) {
            return false;
        }
    }

    private static ArchCondition<JavaMethod> beInterceptableIfProxied() {
        return new ArchCondition<>("not be private, final or static if proxied") {
            @Override
            public void check(JavaMethod method, ConditionEvents events) {
                Set<JavaModifier> modifiers = method.getModifiers();
                Optional<JavaModifier> blocking = Stream.of(
                                JavaModifier.PRIVATE, JavaModifier.FINAL, JavaModifier.STATIC)
                        .filter(modifiers::contains)
                        .findFirst();
                if (blocking.isEmpty()) {
                    return;
                }
                APPLIED_BY_PROXY.stream()
                        .filter(method::isAnnotatedWith)
                        .findFirst()
                        .ifPresent(annotation -> events.add(SimpleConditionEvent.violated(method,
                                method.getDescription() + " is " + blocking.get().name().toLowerCase(Locale.ROOT)
                                        + ", so @" + simpleName(annotation) + " does nothing")));
            }
        };
    }

    private static ArchCondition<JavaMethod> notCallRemoteClientsInsideATransaction() {
        return new ArchCondition<>("not call a remote client inside a transaction") {
            @Override
            public void check(JavaMethod method, ConditionEvents events) {
                if (!transactional(method)) {
                    return;
                }
                for (JavaMethodCall call : method.getMethodCallsFromSelf()) {
                    if (remote(call)) {
                        events.add(SimpleConditionEvent.violated(call, call.getDescription()
                                + " is a remote call inside a transaction"));
                    }
                }
            }
        };
    }

    private static boolean transactional(JavaMethod method) {
        Predicate<String> annotated = name -> method.isAnnotatedWith(name)
                || (method.getModifiers().contains(JavaModifier.PUBLIC) && method.getOwner().isAnnotatedWith(name));
        return annotated.test("org.springframework.transaction.annotation.Transactional")
                || annotated.test("jakarta.transaction.Transactional");
    }

    /** A call on Spring's or the JDK's HTTP clients, an HTTP interface, or an AWS SDK client. */
    private static boolean remote(JavaMethodCall call) {
        JavaClass owner = call.getTargetOwner();
        return REMOTE_CLIENT_PACKAGES.contains(owner.getPackageName())
                || owner.isAssignableTo("software.amazon.awssdk.core.SdkClient")
                || owner.isMetaAnnotatedWith("org.springframework.web.service.annotation.HttpExchange")
                || call.getTarget().resolveMember()
                        .filter(target -> target.isMetaAnnotatedWith(
                                "org.springframework.web.service.annotation.HttpExchange"))
                        .isPresent();
    }

    private static ArchCondition<JavaMember> beLazyIfToOne() {
        return new ArchCondition<>("be lazy if @ManyToOne or @OneToOne") {
            @Override
            public void check(JavaMember member, ConditionEvents events) {
                for (String association : TO_ONE) {
                    member.tryGetAnnotationOfType(association)
                            .filter(annotation -> !enumValue(annotation, "fetch").equals(Optional.of("LAZY")))
                            .ifPresent(annotation -> events.add(SimpleConditionEvent.violated(member,
                                    member.getDescription() + " is @" + simpleName(association)
                                            + " without fetch = LAZY")));
                }
            }
        };
    }

    private static ArchCondition<JavaField> beStoredByNameIfPersistentEnums() {
        return new ArchCondition<>("be stored by name if a persistent enum") {
            @Override
            public void check(JavaField field, ConditionEvents events) {
                JavaClass owner = field.getOwner();
                boolean persistent = owner.isAnnotatedWith("jakarta.persistence.Entity")
                        || owner.isAnnotatedWith("jakarta.persistence.Embeddable")
                        || owner.isAnnotatedWith("jakarta.persistence.MappedSuperclass");
                if (!persistent
                        || field.getModifiers().contains(JavaModifier.STATIC)
                        || field.getModifiers().contains(JavaModifier.TRANSIENT)
                        || CONVERTED.stream().anyMatch(field::isAnnotatedWith)
                        || field.getType().getAllInvolvedRawTypes().stream().noneMatch(JavaClass::isEnum)) {
                    return;
                }
                boolean byName = field.tryGetAnnotationOfType("jakarta.persistence.Enumerated")
                        .flatMap(annotation -> enumValue(annotation, "value"))
                        .filter("STRING"::equals)
                        .isPresent();
                if (!byName) {
                    events.add(SimpleConditionEvent.violated(field,
                            field.getDescription() + " stores the enum by position"));
                }
            }
        };
    }

    /** Empty when the attribute isn't set and its default can't be read, which for these means the default. */
    private static Optional<String> enumValue(JavaAnnotation<?> annotation, String attribute) {
        return annotation.get(attribute)
                .filter(JavaEnumConstant.class::isInstance)
                .map(value -> ((JavaEnumConstant) value).name());
    }

    private static String simpleName(String annotation) {
        return annotation.substring(annotation.lastIndexOf('.') + 1);
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
