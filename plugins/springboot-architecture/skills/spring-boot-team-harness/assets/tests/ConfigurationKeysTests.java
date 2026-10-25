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
import org.jspecify.annotations.Nullable;
import org.junit.jupiter.api.Test;
import org.springframework.boot.env.PropertiesPropertySourceLoader;
import org.springframework.boot.env.PropertySourceLoader;
import org.springframework.boot.env.YamlPropertySourceLoader;
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
            Map<String, Object> document = (Map<String, Object>) new Json(json).value();
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

    /**
     * Reads the metadata JSON without a JSON library. Boot's JsonParserFactory falls back to a parser that
     * returns nested objects as strings when neither Jackson nor Gson is on the test classpath.
     */
    private static final class Json {
        private final String text;
        private int at;

        Json(String text) {
            this.text = text;
        }

        @Nullable Object value() {
            skipSpace();
            char c = text.charAt(at);
            if (c == '{') {
                Map<String, Object> object = new HashMap<>();
                at++;
                while (next() != '}') {
                    String key = string();
                    expect(':');
                    object.put(key, value());
                    if (next() == ',') at++;
                }
                at++;
                return object;
            }
            if (c == '[') {
                List<Object> array = new ArrayList<>();
                at++;
                while (next() != ']') {
                    array.add(value());
                    if (next() == ',') at++;
                }
                at++;
                return array;
            }
            if (c == '"') return string();
            int start = at;
            while (at < text.length() && ",}] \t\r\n".indexOf(text.charAt(at)) < 0) at++;
            String word = text.substring(start, at);
            return switch (word) {
                case "true" -> Boolean.TRUE;
                case "false" -> Boolean.FALSE;
                case "null" -> null;
                default -> word;
            };
        }

        private String string() {
            expect('"');
            StringBuilder out = new StringBuilder();
            while (text.charAt(at) != '"') {
                char c = text.charAt(at++);
                if (c != '\\') {
                    out.append(c);
                    continue;
                }
                char escaped = text.charAt(at++);
                switch (escaped) {
                    case 'n' -> out.append('\n');
                    case 't' -> out.append('\t');
                    case 'r' -> out.append('\r');
                    case 'b' -> out.append('\b');
                    case 'f' -> out.append('\f');
                    case 'u' -> {
                        out.append((char) Integer.parseInt(text.substring(at, at + 4), 16));
                        at += 4;
                    }
                    default -> out.append(escaped);
                }
            }
            at++;
            return out.toString();
        }

        private char next() {
            skipSpace();
            return text.charAt(at);
        }

        private void expect(char c) {
            if (next() != c) {
                throw new IllegalStateException("Expected '" + c + "' at offset " + at + " of configuration metadata");
            }
            at++;
        }

        private void skipSpace() {
            while (at < text.length() && Character.isWhitespace(text.charAt(at))) at++;
        }
    }
}
