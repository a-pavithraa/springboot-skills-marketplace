package com.shop.web;
import com.shop.order.*;
import org.springframework.web.bind.annotation.*;
import java.math.BigDecimal; import java.util.List;
@RestController @RequestMapping("/api/orders")
class OrderHistoryController {
  private final OrderHistoryService history; private final OrderSearchRepository search;
  OrderHistoryController(OrderHistoryService h, OrderSearchRepository s){history=h;search=s;}
  @GetMapping("/history/{customerId}") List<OrderHistoryService.HistoryRow> history(@PathVariable Long customerId){ return history.history(customerId); }
  @GetMapping("/search") List<OrderSearchRepository.Row> search(@RequestParam Long customerId, @RequestParam(defaultValue="id") String sort){ return search.search(customerId, sort); }
  @GetMapping("/revenue") BigDecimal revenue(){ return history.revenueReport(); }
}
