package com.acme.shop.catalog;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.modulith.test.ApplicationModuleTest;

@ApplicationModuleTest(verifyAutomatically = false)
class CatalogModuleTests {
    @Autowired
    Catalog catalog;

    @Test
    void pricesAKnownProduct() {
        assertThat(catalog.priceOf("pen")).hasValueSatisfying(price -> assertThat(price).isEqualByComparingTo("10.00"));
    }
}
