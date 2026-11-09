package com.example.billing.controller;

import com.example.billing.service.InvoiceService;
import java.math.BigDecimal;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/invoices")
public class InvoiceController {

    private final InvoiceService service;

    public InvoiceController(InvoiceService service) {
        this.service = service;
    }

    @GetMapping
    public List<InvoiceView> list() {
        return service.all().stream().map(i -> new InvoiceView(i.getId(), i.getCustomer(), i.getAmount())).toList();
    }

    public record InvoiceView(Long id, String customer, BigDecimal amount) {
    }
}
