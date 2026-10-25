package {{TEST_PACKAGE}};

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
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

    private static final Set<String> SCHEMA_FROM_HIBERNATE = Set.of("update", "create", "create-drop", "create-only");

    @Test
    void bootDependenciesAreNotTestOnly() throws Exception {
        List<String> problems = dependencies().stream()
                .filter(dependency -> dependency.group().equals("org.springframework.boot")
                        && dependency.scope().equals("test")
                        && !dependency.artifact().endsWith("-test")
                        && !TEST_ONLY.contains(dependency.artifact()))
                .map(dependency -> "pom.xml: " + dependency.artifact() + " is on the test classpath only, so the tests pass with it "
                        + "and the application runs without it. Remove <scope>test</scope>")
                .toList();
        assertThat(problems).isEmpty();
    }

    @Test
    void bootAutoConfigurationIsModular() throws Exception {
        List<String> problems = dependencies().stream()
                .filter(dependency -> dependency.group().equals("org.springframework.boot")
                        && dependency.artifact().contains("-classic"))
                .map(dependency -> "pom.xml: " + dependency.artifact() + " brings back Boot 3's all-in-one auto-configuration and "
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
                .as("pom.xml: src/main/resources/db/migration has migrations, but Boot 4 runs them only with "
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

    private record Dependency(String group, String artifact, String scope) {}

    /** The dependencies the pom declares itself; managed versions and profiles don't count. */
    private static List<Dependency> dependencies() throws Exception {
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

    private static String read(Path path) {
        try {
            return Files.readString(path);
        } catch (IOException e) {
            return "";
        }
    }
}
