package com.shop.customer;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
@Service
public class CustomerService {
  private final CustomerRepository repo;
  CustomerService(CustomerRepository repo){this.repo=repo;}
  @Transactional(readOnly=true) public Customer get(Long id){ return repo.findById(id).orElseThrow(); }
}
