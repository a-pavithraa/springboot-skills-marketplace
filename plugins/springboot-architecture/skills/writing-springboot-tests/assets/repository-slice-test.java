package {{PACKAGE}}.catalog.domain;

import {{PACKAGE}}.TestcontainersConfiguration;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest;
import org.springframework.boot.jdbc.test.autoconfigure.AutoConfigureTestDatabase;
import org.springframework.boot.jpa.test.autoconfigure.TestEntityManager;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Persistence slice against the real database in a container: tests YOUR queries, mappings and constraints,
 * not Spring Data's findById. Each test runs in a transaction that rolls back.
 *
 * replace = NONE keeps Boot from swapping in an embedded database: the container is the database.
 */
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import(TestcontainersConfiguration.class)
class ProductRepositoryTest {

    @Autowired
    ProductRepository products;

    @Autowired
    TestEntityManager entityManager;

    @Test
    void findsOnlyActiveProductsWhoseCodeStartsWithThePrefixOrderedByName() {
        persist("LAMP-2", "Desk lamp", true);
        persist("LAMP-1", "Arc lamp", true);
        persist("LAMP-3", "Broken lamp", false);   // inactive: must be left out
        persist("SOFA-1", "Sofa", true);           // other prefix: must be left out
        entityManager.clear();                      // force the query to the database, not the persistence context

        var found = products.findActiveByCodePrefix("LAMP");

        assertThat(found).extracting(Product::getName).containsExactly("Arc lamp", "Desk lamp");
    }

    @Test
    void refusesADuplicateCode() {
        persist("LAMP-1", "Arc lamp", true);

        // saveAndFlush goes through Spring's exception translation; the unique index must reject it
        assertThatThrownBy(() -> products.saveAndFlush(new Product("LAMP-1", "Copy", new BigDecimal("1.00"), true)))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    private void persist(String code, String name, boolean active) {
        entityManager.persistAndFlush(new Product(code, name, new BigDecimal("9.99"), active));
    }
}

// Agent trap: save() then findBy...() in the same transaction returns the cached entity and never runs your
// SQL, so a broken @Query still passes. Flush and clear first, as above.
