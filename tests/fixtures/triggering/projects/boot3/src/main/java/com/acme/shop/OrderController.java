package com.acme.shop;

import java.util.List;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/orders")
class OrderController {
    private final OrderService service;

    OrderController(OrderService service) { this.service = service; }

    @GetMapping List<Order> list() { return service.list(); }

    @GetMapping("/{id}") Order get(@PathVariable Long id) { return service.get(id); }
}
