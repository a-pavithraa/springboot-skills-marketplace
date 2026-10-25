package com.acme.shop;

import static org.assertj.core.api.Assertions.assertThat;

import com.acme.shop.orders.Orders;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class OrdersTests {
    @Autowired
    Orders orders;

    @Test
    void totalsAKnownProduct() {
        assertThat(orders.total("pen", 3)).isEqualByComparingTo("30.00");
    }
}
