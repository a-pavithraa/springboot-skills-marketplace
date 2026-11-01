package com.acme.shop;

import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpStatus;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.stereotype.Component;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@SpringBootApplication
@EnableAsync
@RestController
public class ShopApplication {
    private static final Logger log = LoggerFactory.getLogger(ShopApplication.class);
    private final Pricing pricing;
    private final Confirmations confirmations;
    private final Warehouse warehouse;

    ShopApplication(Pricing pricing, Confirmations confirmations, Warehouse warehouse) {
        this.pricing = pricing;
        this.confirmations = confirmations;
        this.warehouse = warehouse;
    }

    public static void main(String[] args) {
        SpringApplication.run(ShopApplication.class, args);
    }

    record Quote(String customer, int price, int discountPercent) {}

    record OrderRequest(String sku) {}

    record Order(String id, String sku, String status) {}

    @GetMapping("/catalog")
    List<String> catalog() {
        return List.of("A1", "B2");
    }

    @GetMapping("/quotes/{customer}")
    Quote quote(@PathVariable String customer) {
        return new Quote(customer, 100, pricing.discount(customer));
    }

    @PostMapping("/orders")
    @ResponseStatus(HttpStatus.ACCEPTED)
    Order order(@RequestBody OrderRequest request) {
        Order order = new Order("o-1", request.sku(), "ACCEPTED");
        confirmations.send(order);
        return order;
    }

    @GetMapping("/stock/{sku}")
    Map<String, Object> stock(@PathVariable String sku) {
        return Map.of("sku", sku, "available", warehouse.available(sku));
    }

    @Component
    static class Pricing {
        private final RestClient client;

        Pricing(@Value("${shop.pricing-url:http://pricing.internal}") String url) {
            client = RestClient.create(url);
        }

        int discount(String customer) {
            try {
                Integer percent = client.get().uri("/discounts/{id}", customer).retrieve().body(Integer.class);
                return percent == null ? 0 : percent;
            } catch (RestClientException e) {
                log.error("discount lookup failed for {}, quoting list price", customer, e);
                return 0;
            }
        }
    }

    @Component
    static class Confirmations {
        private final RestClient client;

        Confirmations(@Value("${shop.mail-url:http://mail.internal}") String url) {
            client = RestClient.create(url);
        }

        @Async
        public void send(Order order) {
            try {
                client.post().uri("/confirmations").body(order).retrieve().toBodilessEntity();
            } catch (RestClientException e) {
                log.error("confirmation for {} not sent", order.id(), e);
            }
        }
    }

    @Component
    static class Warehouse {
        private static final int ATTEMPTS = 3;
        private static final int LAST_KNOWN = 7;
        private final RestClient client;

        Warehouse(@Value("${shop.warehouse-url:http://warehouse.internal}") String url) {
            client = RestClient.create(url);
        }

        int available(String sku) {
            for (int attempt = 1; attempt <= ATTEMPTS; attempt++) {
                try {
                    Integer count = client.get().uri("/stock/{sku}", sku).retrieve().body(Integer.class);
                    return count == null ? 0 : count;
                } catch (RestClientException e) {
                    log.warn("warehouse call {} of {} failed for {}: {}", attempt, ATTEMPTS, sku, e.getMessage());
                }
            }
            return LAST_KNOWN;
        }
    }
}
