package com.shop.refund;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import java.math.BigDecimal; import java.util.Map;
@Component
class PaymentClient {
  private final RestClient http = RestClient.create("https://payments.internal");
  String refund(String idempotencyKey, String card, BigDecimal amount, String reason) {
    return http.post().uri("/refunds").header("Idempotency-Key", idempotencyKey)
        .body(Map.of("card", card, "amount", amount, "reason", reason)).retrieve().body(String.class);
  }
}
