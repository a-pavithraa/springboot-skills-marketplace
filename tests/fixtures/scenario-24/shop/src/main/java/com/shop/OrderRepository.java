package com.shop;
import org.springframework.data.jpa.repository.JpaRepository;
public interface OrderRepository extends JpaRepository<PurchaseOrder, Long> {}
