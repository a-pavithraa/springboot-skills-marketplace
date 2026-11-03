package com.acme.shop.orders;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.modulith.test.ApplicationModuleTest;
import org.springframework.modulith.test.ApplicationModuleTest.BootstrapMode;

@ApplicationModuleTest(mode = BootstrapMode.DIRECT_DEPENDENCIES, verifyAutomatically = false)
class OrdersModuleTests {
    @Autowired
    Orders orders;

    @Test
    void pricesAnUnknownProductAtZero() {
        assertThat(orders.total("ink", 2)).isEqualByComparingTo("0");
    }
}
