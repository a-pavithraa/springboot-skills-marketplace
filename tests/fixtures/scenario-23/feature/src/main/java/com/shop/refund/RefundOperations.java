package com.shop.refund;
import org.jspecify.annotations.Nullable;
public interface RefundOperations {
  String refund(Long orderId, String cardNumber, java.math.BigDecimal amount, @Nullable String reason);
}
