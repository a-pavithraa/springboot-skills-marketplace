package {{TEST_PACKAGE}};

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.library.freeze.FreezingArchRule.freeze;

import com.tngtech.archunit.base.DescribedPredicate;
import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaMethod;
import com.tngtech.archunit.core.domain.JavaModifier;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchCondition;
import com.tngtech.archunit.lang.ArchRule;
import com.tngtech.archunit.lang.ConditionEvents;
import com.tngtech.archunit.lang.SimpleConditionEvent;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * Production methods that only tests call: dead code its tests keep alive, or an internal opened up so a test can
 * look inside. Not part of the end-of-turn hook, because a service is often written and tested before anything
 * calls it; by verify, before the pull request, everything the change added has a caller or goes. On a codebase
 * that baseline.py recorded, today's cases in src/test/resources/archunit_store are tolerated.
 */
class UnusedCodeTests {

    private static final String BASE_PACKAGE = "{{BASE_PACKAGE}}";

    private static final JavaClasses MAIN = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
            .importPackages(BASE_PACKAGE);

    /** Main and test code together, so a method's callers include the tests. */
    private static final JavaClasses ALL = new ClassFileImporter().importPackages(BASE_PACKAGE);

    private static final Set<String> PRODUCTION =
            MAIN.stream().map(JavaClass::getName).collect(Collectors.toSet());

    private static final boolean RECORDED = Files.isDirectory(Path.of("src/test/resources/archunit_store"))
            || Boolean.getBoolean("archunit.freeze.store.default.allowStoreCreation");

    /** Spring calls these itself, so they have no callers in the code. */
    private static final List<String> ENTRY_POINTS = List.of(
            "org.springframework.web.bind.annotation.RequestMapping",
            "org.springframework.web.bind.annotation.ExceptionHandler",
            "org.springframework.context.annotation.Bean",
            "org.springframework.context.event.EventListener",
            "org.springframework.scheduling.annotation.Scheduled",
            "org.springframework.kafka.annotation.KafkaListener",
            "org.springframework.amqp.rabbit.annotation.RabbitListener",
            "org.springframework.jms.annotation.JmsListener");

    @Test
    void productionMethodsAreNotThereOnlyForTests() {
        ArchRule rule = classes()
                .that(DescribedPredicate.describe("are production classes", type -> PRODUCTION.contains(type.getName())))
                .should(notHaveMethodsOnlyTestsCall())
                .because("nothing in production calls it. If this change is meant to call it, wire that up; "
                        + "otherwise test through the public behaviour and delete it")
                .allowEmptyShould(true);
        (RECORDED ? freeze(rule) : rule).check(ALL);
    }

    /**
     * A method counts when every caller is a test. Getters are left out because Jackson, JPA and templates read
     * them by reflection, and so are methods named in @PreAuthorize-style expressions, which bytecode can't see.
     */
    private static ArchCondition<JavaClass> notHaveMethodsOnlyTestsCall() {
        String expressions = MAIN.stream()
                .flatMap(type -> Stream.concat(Stream.of(type), type.getMethods().stream()))
                .flatMap(element -> element.getAnnotations().stream())
                .filter(annotation -> annotation.getRawType().getPackageName()
                        .equals("org.springframework.security.access.prepost"))
                .map(annotation -> String.valueOf(annotation.get("value").orElse("")))
                .collect(Collectors.joining(" "));
        return new ArchCondition<>("not have methods that only tests call") {
            @Override
            public void check(JavaClass type, ConditionEvents events) {
                if (type.isRecord() || type.isEnum() || type.isInterface() || type.isAnnotation()) {
                    return;
                }
                for (JavaMethod method : type.getMethods()) {
                    Set<JavaModifier> modifiers = method.getModifiers();
                    if (modifiers.contains(JavaModifier.PRIVATE)
                            || modifiers.contains(JavaModifier.PROTECTED)
                            || modifiers.contains(JavaModifier.SYNTHETIC)
                            || (method.getName().matches("(get|is)[A-Z].*") && method.getRawParameterTypes().isEmpty())
                            || ENTRY_POINTS.stream().anyMatch(method::isMetaAnnotatedWith)
                            || overridesAnother(type, method)
                            || expressions.contains("." + method.getName() + "(")) {
                        continue;
                    }
                    Set<String> callers = method.getAccessesToSelf().stream()
                            .map(access -> access.getOriginOwner().getName())
                            .collect(Collectors.toSet());
                    if (!callers.isEmpty() && callers.stream().noneMatch(PRODUCTION::contains)) {
                        events.add(SimpleConditionEvent.violated(
                                method, method.getDescription() + " is called only from tests"));
                    }
                }
            }
        };
    }

    private static boolean overridesAnother(JavaClass type, JavaMethod method) {
        return Stream.concat(type.getAllRawSuperclasses().stream(), type.getAllRawInterfaces().stream())
                .flatMap(other -> other.getMethods().stream())
                .anyMatch(other -> other.getName().equals(method.getName())
                        && other.getRawParameterTypes().size() == method.getRawParameterTypes().size());
    }
}
