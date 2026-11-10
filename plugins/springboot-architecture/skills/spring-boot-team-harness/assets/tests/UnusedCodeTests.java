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
import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Properties;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * Production methods that only tests call: dead code its tests keep alive, or an internal opened up so a test can
 * look inside. Not part of the end-of-turn hook, because a service is often written and tested before anything
 * calls it; by verify, before the pull request, everything the change added has a caller or goes. On a codebase
 * that baseline.py recorded, today's cases in src/test/resources/archunit_store are tolerated. If the record predates
 * this rule, every case fails until baseline.py runs again.
 */
class UnusedCodeTests {

    private static final String BASE_PACKAGE = "{{BASE_PACKAGE}}";

    private static final Pattern PACKAGE = Pattern.compile("^\\s*package\\s+([\\w.]+)\\s*;", Pattern.MULTILINE);

    private static final JavaClasses MAIN = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
            .importPackages(BASE_PACKAGE);

    /** Main and test code together, so a method's callers include the tests. */
    private static final JavaClasses ALL = new ClassFileImporter().importPackages(BASE_PACKAGE);

    private static final Set<String> PRODUCTION =
            MAIN.stream().map(JavaClass::getName).collect(Collectors.toSet());

    private static final DescribedPredicate<JavaClass> HANDWRITTEN = handwritten();

    private static final boolean RECORDING = Boolean.getBoolean("archunit.freeze.store.default.allowStoreCreation");

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
                .that(DescribedPredicate.describe("are production classes",
                        type -> PRODUCTION.contains(type.getName()) && HANDWRITTEN.test(type)))
                .should(notHaveMethodsOnlyTestsCall())
                .because("nothing in production calls it. If this change is meant to call it, wire that up; "
                        + "otherwise test through the public behaviour and delete it. If the user asked for it and "
                        + "nothing is meant to call it yet, don't route existing code through it to pass this rule: "
                        + "stop and ask the user")
                .allowEmptyShould(true);
        (RECORDING || recorded(rule) ? freeze(rule) : rule).check(ALL);
    }

    /** The store files each rule under its description, in this properties file. */
    private static boolean recorded(ArchRule rule) {
        Path index = Path.of("src/test/resources/archunit_store/stored.rules");
        if (!Files.isRegularFile(index)) {
            return false;
        }
        Properties rules = new Properties();
        try (Reader reader = Files.newBufferedReader(index)) {
            rules.load(reader);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return rules.containsKey(rule.getDescription());
    }

    /**
     * A method counts when every caller is a test. Getters and setters are left out because Jackson, JPA, templates
     * and form binding call them by reflection, and so are methods named in @PreAuthorize-style expressions, which
     * bytecode can't see.
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
                            || method.getName().equals("main")
                            || (method.getName().matches("(get|is)[A-Z].*") && method.getRawParameterTypes().isEmpty())
                            || (method.getName().matches("set[A-Z].*") && method.getRawParameterTypes().size() == 1)
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

    /**
     * Leaves out classes compiled from target/generated-sources or build/generated, such as OpenAPI models and MapStruct
     * mappers: the generator writes them, so its configuration is where they change. They still count as callers.
     * Their class files sit beside the team's and @Generated isn't kept in bytecode, so they're named from the
     * generated source files.
     */
    private static DescribedPredicate<JavaClass> handwritten() {
        Set<String> generated = Stream.of(Path.of("target/generated-sources"), Path.of("build/generated"))
                .filter(Files::isDirectory)
                .flatMap(UnusedCodeTests::javaFiles)
                .map(UnusedCodeTests::className)
                .collect(Collectors.toSet());
        return DescribedPredicate.describe("are written by hand", type -> {
            String name = type.getName();
            return !generated.contains(name.contains("$") ? name.substring(0, name.indexOf('$')) : name);
        });
    }

    private static Stream<Path> javaFiles(Path root) {
        try (Stream<Path> files = Files.walk(root)) {
            return files.filter(file -> file.toString().endsWith(".java")).toList().stream();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String className(Path source) {
        String simpleName = source.getFileName().toString().replaceFirst("\\.java$", "");
        try {
            return PACKAGE.matcher(Files.readString(source)).results().findFirst()
                    .map(found -> found.group(1) + "." + simpleName)
                    .orElse(simpleName);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static boolean overridesAnother(JavaClass type, JavaMethod method) {
        return Stream.concat(type.getAllRawSuperclasses().stream(), type.getAllRawInterfaces().stream())
                .flatMap(other -> other.getMethods().stream())
                .anyMatch(other -> other.getName().equals(method.getName())
                        && other.getRawParameterTypes().size() == method.getRawParameterTypes().size());
    }
}
