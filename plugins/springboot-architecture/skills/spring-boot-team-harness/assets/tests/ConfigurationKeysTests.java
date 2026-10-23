package {{TEST_PACKAGE}};

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.boot.env.PropertiesPropertySourceLoader;
import org.springframework.boot.env.PropertySourceLoader;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.boot.json.JsonParserFactory;
import org.springframework.core.env.EnumerablePropertySource;
import org.springframework.core.env.PropertySource;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;

/**
 * Spring Boot ignores a property key that no dependency defines, so a misspelt, renamed or removed key fails
 * silently. This test checks every spring, management, server and logging key in the application's own
 * config files against the configuration metadata of the jars on the classpath.
 */
class ConfigurationKeysTests {

    private static final List<String> CHECKED_PREFIXES = List.of("spring.", "management.", "server.", "logging.");

    private static final String[] METADATA_FILES = {
        "META-INF/spring-configuration-metadata.json", "META-INF/additional-spring-configuration-metadata.json"
    };

    @Test
    void everyBootKeyIsDefinedAndCurrent() throws IOException {
        Metadata metadata = Metadata.load();
        List<String> problems = new ArrayList<>();
        for (Resource file : configFiles()) {
            for (String key : keysIn(file)) {
                if (CHECKED_PREFIXES.stream().noneMatch(key::startsWith)) {
                    continue;
                }
                String canonical = canonical(key);
                if (!metadata.isKnown(canonical)) {
                    problems.add(file.getFilename() + ": " + key + " is defined by no dependency, so Boot ignores it");
                } else if (metadata.deprecations.containsKey(canonical)) {
                    problems.add(
                            file.getFilename() + ": " + key + " is deprecated" + metadata.deprecations.get(canonical));
                }
            }
        }
        assertThat(problems).as("Fix or remove these configuration keys").isEmpty();
    }

    private static List<Resource> configFiles() throws IOException {
        var resolver = new PathMatchingResourcePatternResolver();
        List<Resource> files = new ArrayList<>();
        for (String pattern : List.of("application*.properties", "application*.yml", "application*.yaml")) {
            for (Resource resource : resolver.getResources("classpath*:" + pattern)) {
                if ("file".equals(resource.getURL().getProtocol())) {
                    files.add(resource);
                }
            }
        }
        return files;
    }

    private static Set<String> keysIn(Resource file) throws IOException {
        String name = file.getFilename() == null ? "" : file.getFilename();
        PropertySourceLoader loader =
                name.endsWith(".properties") ? new PropertiesPropertySourceLoader() : new YamlPropertySourceLoader();
        Set<String> keys = new HashSet<>();
        for (PropertySource<?> source : loader.load(name, file)) {
            if (source instanceof EnumerablePropertySource<?> enumerable) {
                keys.addAll(List.of(enumerable.getPropertyNames()));
            }
        }
        return keys;
    }

    /** Relaxed binding: case, dashes, underscores and list indexes don't matter. */
    private static String canonical(String key) {
        return key.replaceAll("\\[[^]]*]", "").toLowerCase().replaceAll("[-_]", "");
    }

    private record Metadata(Set<String> names, Set<String> maps, Map<String, String> deprecations) {

        static Metadata load() throws IOException {
            var metadata = new Metadata(new HashSet<>(), new HashSet<>(), new HashMap<>());
            ClassLoader classLoader = ConfigurationKeysTests.class.getClassLoader();
            for (String file : METADATA_FILES) {
                Enumeration<URL> urls = classLoader.getResources(file);
                while (urls.hasMoreElements()) {
                    try (InputStream in = urls.nextElement().openStream()) {
                        metadata.add(new String(in.readAllBytes(), StandardCharsets.UTF_8));
                    }
                }
            }
            return metadata;
        }

        @SuppressWarnings("unchecked")
        private void add(String json) {
            Map<String, Object> document = JsonParserFactory.getJsonParser().parseMap(json);
            for (Object item : (List<Object>) document.getOrDefault("properties", List.of())) {
                Map<String, Object> property = (Map<String, Object>) item;
                String name = canonical(String.valueOf(property.get("name")));
                names.add(name);
                if (String.valueOf(property.get("type")).startsWith("java.util.Map")) {
                    maps.add(name);
                }
                if (property.get("deprecation") instanceof Map<?, ?> deprecation) {
                    Object replacement = deprecation.get("replacement");
                    deprecations.put(name, replacement == null ? "" : ", use " + replacement);
                } else if (Boolean.TRUE.equals(property.get("deprecated"))) {
                    deprecations.put(name, "");
                }
            }
            for (Object item : (List<Object>) document.getOrDefault("groups", List.of())) {
                Map<String, Object> group = (Map<String, Object>) item;
                if (String.valueOf(group.get("type")).startsWith("java.util.Map")) {
                    maps.add(canonical(String.valueOf(group.get("name"))));
                }
            }
        }

        boolean isKnown(String canonical) {
            return names.contains(canonical) || maps.stream().anyMatch(map -> canonical.startsWith(map + "."));
        }
    }
}
