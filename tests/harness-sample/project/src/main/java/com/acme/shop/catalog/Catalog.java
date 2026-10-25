package com.acme.shop.catalog;

import java.math.BigDecimal;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class Catalog {
    private final Map<String, BigDecimal> prices = Map.of("pen", new BigDecimal("10.00"));

    public Optional<BigDecimal> priceOf(String sku) {
        return Optional.ofNullable(prices.get(sku));
    }
}
