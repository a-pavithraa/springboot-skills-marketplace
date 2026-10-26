package com.acme.shop.orders;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/** Logs the price of one pen at startup, so the sample has a production caller of Orders.total. */
@Component
class OpeningTotals {

    private static final Logger LOG = LoggerFactory.getLogger(OpeningTotals.class);

    private final Orders orders;

    OpeningTotals(Orders orders) {
        this.orders = orders;
    }

    @EventListener(ApplicationReadyEvent.class)
    void logPenPrice() {
        LOG.info("One pen costs {}", orders.total("pen", 1));
    }
}
