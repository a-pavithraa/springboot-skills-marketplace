package com.shop.refund;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.constraints.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import java.math.BigDecimal;
@RestController @RequestMapping("/api/refunds")
class RefundController {
  record RefundRequest(@NotNull Long orderId, @NotBlank String cardNumber, @Positive BigDecimal amount, String reason) {}
  private final RefundOperations refunds;
  private final ObjectMapper mapper = new ObjectMapper();
  RefundController(RefundOperations refunds){this.refunds=refunds;}

  @PreAuthorize("hasRole('SUPPORT')")
  @PostMapping
  String refund(@RequestBody RefundRequest req) throws Exception {
    String id = refunds.refund(req.orderId(), req.cardNumber(), req.amount(), req.reason());
    return mapper.writeValueAsString(java.util.Map.of("refundId", id));
  }
}
