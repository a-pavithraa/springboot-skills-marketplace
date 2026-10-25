package com.shop.admin;
import com.shop.customer.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import java.util.List;
@RestController @RequestMapping("/api/admin/customers")
class AdminController {
  private final CustomerRepository customers;
  AdminController(CustomerRepository customers){this.customers=customers;}

  @PreAuthorize("hasRole('ADMIN')")
  @GetMapping("/{id}")
  Customer get(@PathVariable Long id) { return customers.findById(id).orElseThrow(); }

  @PreAuthorize("hasRole('ADMIN')")
  @GetMapping
  List<Customer> list() { return customers.findAll(); }

  @DeleteMapping("/{id}")
  void delete(@PathVariable Long id) { customers.deleteById(id); }
}
