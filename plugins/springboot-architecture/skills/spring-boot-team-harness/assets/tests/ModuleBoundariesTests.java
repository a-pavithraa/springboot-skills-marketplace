package {{TEST_PACKAGE}};

import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;

/**
 * Each direct subpackage of the application package is a module. Other modules may use only its top-level
 * package; anything in a nested package is internal. Cycles between modules fail too.
 */
class ModuleBoundariesTests {

    @Test
    void modulesRespectTheirBoundaries() {
        ApplicationModules.of({{APP_CLASS}}.class).verify();
    }
}
