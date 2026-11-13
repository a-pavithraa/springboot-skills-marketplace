package {{TEST_PACKAGE}};

import static org.assertj.core.api.Assertions.assertThat;

import com.tngtech.archunit.base.DescribedPredicate;
import com.tngtech.archunit.core.domain.JavaAnnotation;
import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaMethod;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Predicate;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import org.junit.jupiter.api.Test;
import org.springframework.boot.env.PropertiesPropertySourceLoader;
import org.springframework.boot.env.PropertySourceLoader;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.core.env.EnumerablePropertySource;
import org.springframework.core.env.PropertySource;
import org.springframework.core.io.FileSystemResource;
import org.w3c.dom.Element;
import org.w3c.dom.Node;

/**
 * Shortcuts that make the tests pass while production runs without the feature: a dependency added only to the
 * test classpath, Boot 3's auto-configuration brought back, and a schema that doesn't come from the migrations.
 */
class BuildSetupTests {

    /** Boot artifacts that belong on the test classpath. */
    private static final Set<String> TEST_ONLY = Set.of("spring-boot-testcontainers", "spring-boot-docker-compose");

    /**
     * HTTP client starters, with what main code uses from them. Tests often use one to call the running app; it
     * belongs in production only when main code builds a client with it.
     */
    private static final Map<String, List<String>> HTTP_CLIENTS = Map.of(
            "spring-boot-starter-restclient", List.of("RestClient.Builder", "RestTemplateBuilder", "@HttpExchange",
                    "@ImportHttpServices"),
            "spring-boot-starter-webclient", List.of("WebClient.Builder", "@HttpExchange", "@ImportHttpServices"));

    /** Set by the harness's Gradle script, which writes the build's declared dependencies there. */
    private static final String DECLARED = System.getProperty("harness.declaredDependencies");

    private static final String BUILD_FILE = System.getProperty("harness.buildFile", "pom.xml");

    private static final String BASE_PACKAGE = "{{BASE_PACKAGE}}";

    private static final Pattern PACKAGE = Pattern.compile("^\\s*package\\s+([\\w.]+)\\s*;", Pattern.MULTILINE);

    private static final DescribedPredicate<JavaClass> HANDWRITTEN = handwritten();

    private static final JavaClasses MAIN = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
            .importPackages(BASE_PACKAGE)
            .that(HANDWRITTEN);

    private static final String SCHEDULED = "org.springframework.scheduling.annotation.Scheduled";

    private static final String SCHEDULES = "org.springframework.scheduling.annotation.Schedules";

    /** A bean of one of these types, or a SchedulingConfigurer, replaces Boot's one-thread scheduler. */
    private static final List<String> OWN_SCHEDULERS = List.of(
            "org.springframework.scheduling.TaskScheduler", "java.util.concurrent.ScheduledExecutorService");

    /** A whole-value placeholder, with its default if it has one. */
    private static final Pattern PLACEHOLDER = Pattern.compile("^\\$\\{[^:}]+(?::(.*))?}$");

    private static final Set<String> SCHEMA_FROM_HIBERNATE = Set.of("update", "create", "create-drop", "create-only");

    @Test
    void bootDependenciesAreNotTestOnly() throws Exception {
        List<String> problems = dependencies().stream()
                .filter(dependency -> dependency.group().equals("org.springframework.boot")
                        && dependency.scope().equals("test")
                        && !dependency.artifact().endsWith("-test")
                        && !TEST_ONLY.contains(dependency.artifact())
                        && !onlyTestsCallOverHttp(dependency.artifact()))
                .map(dependency -> BUILD_FILE + ": " + dependency.artifact() + " is on the test classpath only, so the tests pass with it "
                        + "and the application runs without it. "
                        + (DECLARED == null ? "Remove <scope>test</scope>" : "Declare it with implementation"))
                .toList();
        assertThat(problems).isEmpty();
    }

    @Test
    void bootAutoConfigurationIsModular() throws Exception {
        List<String> problems = dependencies().stream()
                .filter(dependency -> dependency.group().equals("org.springframework.boot")
                        && dependency.artifact().contains("-classic"))
                .map(dependency -> BUILD_FILE + ": " + dependency.artifact() + " brings back Boot 3's all-in-one auto-configuration and "
                        + "hides which modules the application needs. Remove it and add the starter for the feature "
                        + "that stopped working, for example spring-boot-starter-flyway")
                .toList();
        assertThat(problems).isEmpty();
    }

    @Test
    void flywayMigrationsRun() throws Exception {
        // An app with more than one database often builds Flyway itself for one of them, and then it migrates.
        if (!hasFiles(Path.of("src/main/resources/db/migration")) || buildsFlywayItself()) {
            return;
        }
        boolean runs = dependencies().stream()
                .anyMatch(dependency -> dependency.group().equals("org.springframework.boot")
                        && !dependency.scope().equals("test")
                        && (dependency.artifact().equals("spring-boot-starter-flyway")
                                || dependency.artifact().equals("spring-boot-flyway")));
        assertThat(runs)
                .as(BUILD_FILE + ": src/main/resources/db/migration has migrations, but Boot 4 runs them only with "
                        + "spring-boot-starter-flyway; flyway-core alone never migrates. Add the starter")
                .isTrue();
    }

    @Test
    void schemaComesFromMigrations() throws IOException {
        if (!hasFiles(Path.of("src/main/resources/db/migration"))
                && !hasFiles(Path.of("src/main/resources/db/changelog"))) {
            return;
        }
        List<String> problems = new ArrayList<>();
        for (Path file : configFiles()) {
            for (PropertySource<?> source : load(file)) {
                if (!(source instanceof EnumerablePropertySource<?> enumerable)) {
                    continue;
                }
                for (String key : enumerable.getPropertyNames()) {
                    String canonical = key.toLowerCase().replaceAll("[-_]", "");
                    String value = String.valueOf(enumerable.getProperty(key)).trim().toLowerCase();
                    boolean hibernate = (canonical.equals("spring.jpa.hibernate.ddlauto")
                                    || canonical.equals("spring.jpa.properties.hibernate.hbm2ddl.auto"))
                            && SCHEMA_FROM_HIBERNATE.contains(value);
                    boolean generated = canonical.equals("spring.jpa.generateddl") && value.equals("true");
                    if (hibernate || generated) {
                        problems.add(file + ": " + key + "=" + value + " lets Hibernate change the schema, so it "
                                + "drifts from the migrations. Write a migration, and set ddl-auto to validate or "
                                + "none");
                    }
                }
            }
        }
        try (Stream<Path> sources = Files.walk(Path.of("src/main/java"))) {
            sources.filter(path -> path.toString().endsWith(".java"))
                    .filter(path -> read(path).contains("flyway_schema_history"))
                    .forEach(path -> problems.add(path + " writes Flyway's history table, so Flyway skips migrations "
                            + "that never ran. Let Flyway run them"));
        }
        assertThat(problems).isEmpty();
    }

    /**
     * Boot's scheduler has one thread, so one slow job delays the rest. With virtual threads it starts a thread per
     * run, except for fixedDelay jobs, which Spring keeps on the one scheduler thread.
     */
    @Test
    void scheduledJobsDontShareOneThread() throws IOException {
        List<Job> jobs = MAIN.stream()
                .flatMap(type -> type.getMethods().stream())
                .flatMap(BuildSetupTests::jobsOf)
                .sorted(Comparator.comparing(Job::name))
                .toList();
        if (jobs.size() < 2 || runsItsOwnScheduler()) {
            return;
        }
        boolean pooled = false;
        boolean virtual = false;
        for (Path file : configFiles()) {
            if (!file.startsWith(Path.of("src/main/resources"))) {
                continue;
            }
            for (PropertySource<?> source : load(file)) {
                if (!(source instanceof EnumerablePropertySource<?> enumerable)) {
                    continue;
                }
                for (String key : enumerable.getPropertyNames()) {
                    String canonical = key.toLowerCase().replaceAll("[-_]", "");
                    String value = String.valueOf(enumerable.getProperty(key));
                    pooled |= canonical.equals("spring.task.scheduling.pool.size")
                            && chosen(value, size -> size.matches("\\d+") && Integer.parseInt(size) > 1);
                    virtual |= canonical.equals("spring.threads.virtual.enabled")
                            && chosen(value, "true"::equalsIgnoreCase);
                }
            }
        }
        List<String> fixedDelay = jobs.stream().filter(Job::fixedDelay).map(Job::name).toList();
        assertThat(pooled || (virtual && fixedDelay.isEmpty()))
                .as("src/main/java has " + jobs.size() + " @Scheduled jobs ("
                        + jobs.stream().map(Job::name).collect(Collectors.joining(", "))
                        + "), and Boot runs them all on one scheduler thread, so one slow job delays the rest. Set "
                        + "spring.task.scheduling.pool.size to the number of jobs that may run at once"
                        + (fixedDelay.isEmpty()
                                ? ", or spring.threads.virtual.enabled=true"
                                : "; virtual threads don't help fixedDelay jobs (" + String.join(", ", fixedDelay)
                                        + ")"))
                .isTrue();
    }

    private record Job(JavaMethod method, JavaAnnotation<?> scheduled) {

        String name() {
            return method.getOwner().getSimpleName() + "." + method.getName() + "()";
        }

        boolean fixedDelay() {
            return scheduled.tryGetExplicitlyDeclaredProperty("fixedDelay")
                            .filter(delay -> !delay.equals(-1L))
                            .isPresent()
                    || scheduled.tryGetExplicitlyDeclaredProperty("fixedDelayString")
                            .filter(delay -> !String.valueOf(delay).isEmpty())
                            .isPresent();
        }
    }

    /** One job per trigger: @Scheduled, each entry of @Schedules, or an annotation that carries @Scheduled. */
    private static Stream<Job> jobsOf(JavaMethod method) {
        return method.getAnnotations().stream().flatMap(annotation -> {
            String type = annotation.getRawType().getName();
            if (type.equals(SCHEDULED)) {
                return Stream.of(new Job(method, annotation));
            }
            if (type.equals(SCHEDULES)) {
                return annotation.get("value").filter(Object[].class::isInstance).stream()
                        .flatMap(entries -> Arrays.stream((Object[]) entries))
                        .filter(JavaAnnotation.class::isInstance)
                        .map(entry -> new Job(method, (JavaAnnotation<?>) entry));
            }
            Optional<? extends JavaAnnotation<?>> carried = annotation.getRawType().tryGetAnnotationOfType(SCHEDULED);
            return carried.stream().map(scheduled -> new Job(method, scheduled));
        });
    }

    private static boolean runsItsOwnScheduler() {
        return MAIN.stream().anyMatch(type ->
                type.isAssignableTo("org.springframework.scheduling.annotation.SchedulingConfigurer")
                        || type.getMethods().stream()
                                .filter(method -> method.isAnnotatedWith("org.springframework.context.annotation.Bean"))
                                .anyMatch(method -> OWN_SCHEDULERS.stream()
                                        .anyMatch(method.getRawReturnType()::isAssignableTo)));
    }

    /**
     * A literal that passes, or a placeholder whose default passes. A placeholder with no default stops the app from
     * starting until it is set, so someone chose the value.
     */
    private static boolean chosen(String value, Predicate<String> enough) {
        Matcher placeholder = PLACEHOLDER.matcher(value.strip());
        if (placeholder.matches()) {
            return placeholder.group(1) == null || enough.test(placeholder.group(1).strip());
        }
        return enough.test(value.strip());
    }

    private record Dependency(String group, String artifact, String scope) {}

    /** The dependencies the build declares itself; managed versions and profiles don't count. */
    private static List<Dependency> dependencies() throws Exception {
        if (DECLARED != null) {
            return Files.readAllLines(Path.of(DECLARED)).stream()
                    .filter(line -> !line.isBlank())
                    .map(line -> {
                        String[] scopeAndModule = line.split(" ", 2);
                        String[] module = scopeAndModule[1].split(":", 2);
                        String scope = scopeAndModule[0].equals("compile") ? "" : scopeAndModule[0];
                        return new Dependency(module[0], module[1], scope);
                    })
                    .toList();
        }
        var factory = DocumentBuilderFactory.newInstance();
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        Element project = factory.newDocumentBuilder().parse(Path.of("pom.xml").toFile()).getDocumentElement();
        List<Dependency> dependencies = new ArrayList<>();
        for (Element list : children(project, "dependencies")) {
            for (Element dependency : children(list, "dependency")) {
                dependencies.add(new Dependency(
                        text(dependency, "groupId"), text(dependency, "artifactId"), text(dependency, "scope")));
            }
        }
        return dependencies;
    }

    private static List<Element> children(Element parent, String name) {
        List<Element> found = new ArrayList<>();
        for (Node node = parent.getFirstChild(); node != null; node = node.getNextSibling()) {
            if (node instanceof Element element && element.getTagName().equals(name)) {
                found.add(element);
            }
        }
        return found;
    }

    private static String text(Element parent, String name) {
        return children(parent, name).stream()
                .map(element -> element.getTextContent().trim())
                .findFirst()
                .orElse("");
    }

    private static boolean onlyTestsCallOverHttp(String artifact) {
        List<String> uses = HTTP_CLIENTS.get(artifact);
        if (uses == null) {
            return false;
        }
        try (Stream<Path> sources = Files.walk(Path.of("src/main/java"))) {
            return sources.filter(path -> path.toString().endsWith(".java"))
                    .map(BuildSetupTests::read)
                    .noneMatch(source -> uses.stream().anyMatch(source::contains));
        } catch (IOException e) {
            return false;
        }
    }

    private static boolean buildsFlywayItself() throws IOException {
        try (Stream<Path> sources = Files.walk(Path.of("src/main/java"))) {
            return sources.filter(path -> path.toString().endsWith(".java"))
                    .map(BuildSetupTests::read)
                    .anyMatch(source -> source.contains("Flyway.configure(") || source.contains("new Flyway("));
        }
    }

    private static boolean hasFiles(Path directory) throws IOException {
        if (!Files.isDirectory(directory)) {
            return false;
        }
        try (Stream<Path> files = Files.walk(directory)) {
            return files.anyMatch(Files::isRegularFile);
        }
    }

    private static List<Path> configFiles() throws IOException {
        List<Path> files = new ArrayList<>();
        for (Path resources : List.of(Path.of("src/main/resources"), Path.of("src/test/resources"))) {
            if (!Files.isDirectory(resources)) {
                continue;
            }
            try (Stream<Path> found = Files.list(resources)) {
                found.filter(path -> path.getFileName().toString().matches("application.*\\.(properties|ya?ml)"))
                        .forEach(files::add);
            }
        }
        return files;
    }

    private static List<PropertySource<?>> load(Path file) throws IOException {
        String name = file.getFileName().toString();
        PropertySourceLoader loader =
                name.endsWith(".properties") ? new PropertiesPropertySourceLoader() : new YamlPropertySourceLoader();
        return loader.load(name, new FileSystemResource(file));
    }

    /**
     * Leaves out classes compiled from target/generated-sources or build/generated, such as OpenAPI models and MapStruct
     * mappers: the generator writes them, so its configuration is where they change. Their class files sit beside the
     * team's and @Generated isn't kept in bytecode, so they're named from the generated source files.
     */
    private static DescribedPredicate<JavaClass> handwritten() {
        Set<String> generated = Stream.of(Path.of("target/generated-sources"), Path.of("build/generated"))
                .filter(Files::isDirectory)
                .flatMap(BuildSetupTests::javaFiles)
                .map(BuildSetupTests::className)
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

    private static String read(Path path) {
        try {
            return Files.readString(path);
        } catch (IOException e) {
            return "";
        }
    }
}
