package com.shop.refund;
import org.slf4j.Logger; import org.slf4j.LoggerFactory;
import org.springframework.resilience.annotation.Retryable;
import org.springframework.stereotype.Service;
import java.math.BigDecimal; import java.util.UUID;
@Service
public class RefundService implements RefundOperations {
  private static final Logger log = LoggerFactory.getLogger(RefundService.class);
  private final PaymentClient payments;
  RefundService(PaymentClient payments){this.payments=payments;}

  @Override
  @Retryable(maxRetries = 3)
  public String refund(Long orderId, String cardNumber, BigDecimal amount, String reason) {
    log.info("Refunding order {} to card {} amount {}", orderId, cardNumber, amount);
    String idempotencyKey = UUID.randomUUID().toString();
    return payments.refund(idempotencyKey, cardNumber, amount, reason.trim());
  }
}
