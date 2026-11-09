package com.example.billing.service;

import com.example.billing.domain.Invoice;
import com.example.billing.repository.InvoiceRepository;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class InvoiceService {

    private final InvoiceRepository invoices;

    public InvoiceService(InvoiceRepository invoices) {
        this.invoices = invoices;
    }

    @Transactional(readOnly = true)
    public List<Invoice> all() {
        return invoices.findAll();
    }
}
