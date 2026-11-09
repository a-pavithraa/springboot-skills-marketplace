package com.example.orders;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

/**
 * Calculates order discounts and manages orders.
 *
 * <p>Discount rules (applied in order, only the first matching rule applies):
 * <ul>
 *   <li>quantity >= 100: 20% discount</li>
 *   <li>quantity >= 50: 15% discount</li>
 *   <li>quantity >= 10: 10% discount</li>
 *   <li>quantity == 1: no discount (0%)</li>
 *   <li>quantity == 0: illegal — throws IllegalArgumentException</li>
 *   <li>quantity < 0: illegal — throws IllegalArgumentException</li>
 * </ul>
 *
 * <p>The returned discount amount is always rounded half-up to 2 decimal places.
 * Price is in whole dollars (not cents). The discount amount must never exceed
 * the original price * quantity.
 */
public class OrderService {

    /**
     * Calculates the discount amount for a given quantity and unit price.
     *
     * @param quantity number of items; must be >= 1
     * @param unitPrice price per item in dollars; must be positive
     * @return discount amount in dollars, rounded half-up to 2 decimal places
     * @throws IllegalArgumentException if quantity <= 0 or unitPrice is not positive
     */
    public BigDecimal calculateDiscount(int quantity, BigDecimal unitPrice) {
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity must be >= 1, got: " + quantity);
        }
        if (unitPrice == null || unitPrice.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("unitPrice must be positive");
        }

        BigDecimal rate;
        if (quantity >= 100) {
            rate = new BigDecimal("0.20");
        } else if (quantity >= 50) {
            rate = new BigDecimal("0.15");
        } else if (quantity >= 10) {
            rate = new BigDecimal("0.10");
        } else {
            rate = BigDecimal.ZERO;
        }

        BigDecimal total = unitPrice.multiply(BigDecimal.valueOf(quantity));
        return total.multiply(rate).setScale(2, RoundingMode.HALF_UP);
    }

    /**
     * Returns all orders visible to the caller. Requires ROLE_USER or ROLE_ADMIN.
     */
    public List<Order> listOrders() {
        // implementation omitted
        return List.of();
    }

    /**
     * Creates a new order. Requires ROLE_ADMIN.
     *
     * @param order the order to create; must not be null
     * @return the saved order with its assigned id
     */
    public Order createOrder(Order order) {
        // implementation omitted
        return order;
    }
}
