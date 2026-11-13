package {{TEST_PACKAGE}};

import static org.assertj.core.api.Assertions.assertThat;

import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaModifier;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.springframework.asm.ClassReader;
import org.springframework.modulith.core.ApplicationModule;
import org.springframework.modulith.core.ApplicationModules;
import org.springframework.modulith.core.NamedInterface;

/**
 * Each direct subpackage of the application package is a module. Other modules may use only its top-level package
 * and its named interfaces; anything else is internal. Cycles between modules fail too, and so do modules that depend
 * on one their {@code allowedDependencies} leave out.
 *
 * <p>Violations recorded in {@code src/test/resources/modulith_store} are older than the harness and tolerated. Only
 * the harness's baseline.py adds to that record; a fixed violation drops out of it on the next run of this test.
 * Without the record, every violation fails.
 */
class ModuleBoundariesTests {

    private static final String STORE_PATH = "src/test/resources/modulith_store";
    private static final Path STORE = Path.of(STORE_PATH);
    private static final int CONSTANT_CLASS = 7;

    @Test
    void modulesRespectTheirBoundaries() throws IOException {
        var violations = violations(ApplicationModules.of({{APP_CLASS}}.class));
        if (Boolean.getBoolean("modulith.store.record")) {
            write(violations.keySet());
            return;
        }
        Set<String> recorded = Files.exists(STORE) ? Set.copyOf(Files.readAllLines(STORE)) : Set.of();
        var stillPresent = new TreeSet<>(recorded);
        stillPresent.retainAll(violations.keySet());
        if (stillPresent.size() < recorded.size()) {
            write(stillPresent);
        }
        var unrecorded = violations.entrySet().stream()
                .filter(violation -> !recorded.contains(violation.getKey()))
                .map(Map.Entry::getValue)
                .toList();
        assertThat(unrecorded)
                .as("%d module-boundary violations are new (%d older ones are recorded in %s)",
                        unrecorded.size(), stillPresent.size(), STORE_PATH)
                .isEmpty();
    }

    /**
     * Spring Modulith's violations, published constructors that take internal types, and allowed dependencies nothing
     * uses, keyed by {@link Key}.
     */
    private static Map<String, String> violations(ApplicationModules modules) {
        var found = new LinkedHashMap<String, String>();
        modules.detectViolations().getMessages().forEach(message -> found.putIfAbsent(Key.of(message), message));
        internalTypesInPublicConstructors(modules).forEach(leak -> found.putIfAbsent("leak|" + leak, leak));
        unusedAllowedDependencies(modules).forEach((key, message) -> found.putIfAbsent(key, message));
        return found;
    }

    // An allowed dependency nothing uses lets a future dependency in without review: the guard hook and the integrity
    // check stop an agent widening allowedDependencies, but not using an entry that is already there.
    private static Map<String, String> unusedAllowedDependencies(ApplicationModules modules) {
        var unused = new TreeMap<String, String>();
        for (var module : modules) {
            var used = module.getDirectDependencies(modules).stream().toList();
            var named = module.getBasePackage().stream()
                    .flatMap(ModuleBoundariesTests::classesInConstantPool)
                    .collect(Collectors.toSet());
            for (var allowed : module.getAllowedDependencies(modules)) {
                var target = allowed.getTargetModule();
                var namedInterface = allowed.getTargetNamedInterface();
                if (used.stream().noneMatch(dependency -> dependency.getTargetModule().equals(target)
                                && (namedInterface == null || namedInterface.contains(dependency.getTargetType())))
                        && named.stream()
                                .flatMap(name -> target.getType(name).stream())
                                .noneMatch(type -> namedInterface == null || namedInterface.contains(type))) {
                    var entry = namedInterface == null || namedInterface.isUnnamed()
                            ? target.getIdentifier().toString()
                            : target.getIdentifier() + " :: " + namedInterface.getName();
                    unused.put("unused-allowance|" + module.getIdentifier() + "|" + entry,
                            "Module '%s' allows a dependency on '%s' that no code uses. Remove it from allowedDependencies."
                                    .formatted(module.getIdentifier(), entry));
                }
            }
        }
        return unused;
    }

    // javac copies a compile-time constant into the class that reads it, so a module whose only use of another is
    // such a constant has no dependency ArchUnit sees. javac still names the constant's class in the constant pool.
    private static Stream<String> classesInConstantPool(JavaClass type) {
        var source = type.getSource();
        if (source.isEmpty()) {
            return Stream.empty();
        }
        try (var in = source.get().getUri().toURL().openStream()) {
            var reader = new ClassReader(in);
            var buffer = new char[reader.getMaxStringLength()];
            return IntStream.range(1, reader.getItemCount())
                    .map(reader::getItem)
                    .filter(offset -> offset > 0 && reader.readByte(offset - 1) == CONSTANT_CLASS)
                    .mapToObj(offset -> reader.readUTF8(offset, buffer).replace('/', '.'))
                    .toList()
                    .stream();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static void write(Set<String> keys) throws IOException {
        if (keys.isEmpty()) {
            Files.deleteIfExists(STORE);
            return;
        }
        Files.createDirectories(STORE.getParent());
        Files.writeString(STORE, keys.stream().sorted().collect(Collectors.joining("\n", "", "\n")));
    }

    // verify() lets other modules use any type a published class names in a public signature, so a public
    // constructor taking an internal bean would quietly publish that bean too. Generic and array parameters count, as
    // Optional<X>, List<X> or X[] hands X to the caller as well. A record's components are the data it returns,
    // published on purpose, so records are skipped.
    private static Set<String> internalTypesInPublicConstructors(ApplicationModules modules) {
        return modules.stream()
                .filter(module -> !module.isOpen())
                .flatMap(module -> module.getNamedInterfaces().stream()
                        .flatMap(NamedInterface::asJavaClasses)
                        .filter(published -> declaredPublished(module, published))
                        .filter(published -> !published.isRecord())
                        .flatMap(published -> published.getConstructors().stream())
                        .filter(constructor -> constructor.getModifiers().contains(JavaModifier.PUBLIC))
                        .flatMap(constructor -> constructor.getParameterTypes().stream()
                                .flatMap(type -> type.getAllInvolvedRawTypes().stream())
                                .distinct()
                                .filter(module::contains)
                                .filter(type -> !declaredPublished(module, type))
                                .map(type -> constructor.getFullName() + " takes internal " + type.getName())))
                .collect(Collectors.toCollection(TreeSet::new));
    }

    // NamedInterface.contains() already counts the types a published class names, so ask what was declared: the
    // module's root package, or an @NamedInterface on the class or its package.
    private static boolean declaredPublished(ApplicationModule module, JavaClass type) {
        var outermost = type;
        while (outermost.getEnclosingClass().isPresent()) {
            outermost = outermost.getEnclosingClass().get();
        }
        return type.getPackageName().equals(module.getBasePackage().getName())
                || outermost.isAnnotatedWith(org.springframework.modulith.NamedInterface.class)
                || type.getPackage().isAnnotatedWith(org.springframework.modulith.NamedInterface.class);
    }

    /**
     * What a violation is, without where it is: a comment added above a recorded violation must not make it new.
     * A cycle is keyed by the modules in it, so another call along a recorded cycle passes while a new cycle, or a
     * module joining one, fails. A dependency that {@code allowedDependencies} leaves out is keyed by the two modules.
     */
    static final class Key {

        private static final Pattern LOCATION = Pattern.compile(" in \\([^()]+\\.(?:java|kt):\\d+\\)");
        private static final Pattern CYCLE_SLICE = Pattern.compile("Slice (\\S+)");
        private static final Pattern DEPENDENCY = Pattern.compile("^Module '([^']+)' depends on module '([^']+)' via ");

        static String of(String message) {
            if (message.startsWith("Cycle detected:")) {
                var path = message.lines().takeWhile(line -> !line.matches("\\s*1\\. .*")).collect(Collectors.joining(" "));
                var slices = new TreeSet<String>();
                CYCLE_SLICE.matcher(path).results().forEach(slice -> slices.add(slice.group(1)));
                return "cycle|" + String.join(",", slices);
            }
            var dependency = DEPENDENCY.matcher(message);
            if (dependency.find()) {
                return "dependency|" + dependency.group(1) + "|" + dependency.group(2);
            }
            var flat = LOCATION.matcher(message).replaceAll("").replaceAll("\\s+", " ").strip();
            return (message.contains("depends on non-exposed type") ? "internal|" : "other|") + flat;
        }
    }
}
