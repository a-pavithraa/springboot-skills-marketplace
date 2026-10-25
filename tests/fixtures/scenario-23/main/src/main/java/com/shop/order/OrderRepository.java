package com.shop.order;
import org.springframework.data.jpa.repository.JpaRepository; import java.util.List;
/** orders holds about 2 million rows in production. */
public interface OrderRepository extends JpaRepository<Order, Long> {
  List<Order> findByCustomerId(Long customerId);
}
