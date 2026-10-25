package com.shop.web;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/orders")
class OrderController {
  @PreAuthorize("hasRole('ADMIN')") @DeleteMapping("/{id}") void cancel(@PathVariable Long id) {}
}
