package com.shop;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import java.util.*;
@RestController @RequestMapping("/api")
class ShopController {
  private final OrderService orders; private final ProductService products;
  ShopController(OrderService orders, ProductService products) { this.orders = orders; this.products = products; }
  @GetMapping("/orders") List<OrderService.OrderSummary> list() { return orders.list(); }
  @GetMapping("/orders/{id}") OrderService.OrderDetail get(@PathVariable Long id) { return orders.get(id); }
  @DeleteMapping("/orders/{id}/lines/{lineId}") @ResponseStatus(HttpStatus.NO_CONTENT)
  void removeLine(@PathVariable Long id, @PathVariable Long lineId) { orders.removeLine(id, lineId); }
  @PostMapping("/products/reprice") @ResponseStatus(HttpStatus.NO_CONTENT)
  void reprice(@RequestParam int percent) { products.reprice(percent); }
  @ExceptionHandler(NoSuchElementException.class) @ResponseStatus(HttpStatus.NOT_FOUND) void notFound() {}
}
