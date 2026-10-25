package com.acme.shop.orders;

import com.acme.shop.catalog.Catalog;
import java.math.BigDecimal;
import org.springframework.stereotype.Service;

@Service
public class Orders {
    private final Catalog catalog;

    Orders(Catalog catalog) {
        this.catalog = catalog;
    }

    public BigDecimal total(String sku, int quantity) {
        return catalog.priceOf(sku).orElse(BigDecimal.ZERO).multiply(BigDecimal.valueOf(quantity));
    }
}
