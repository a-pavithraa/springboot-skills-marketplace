package com.shop;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal; import java.math.RoundingMode;
@Service
public class ProductService {
  private final ProductRepository products;
  ProductService(ProductRepository products) { this.products = products; }

  /** Applies a price change to the whole catalogue (about 50,000 products). */
  @Transactional
  public void reprice(int percent) {
    BigDecimal factor = BigDecimal.valueOf(100 + percent).divide(BigDecimal.valueOf(100));
    for (Product p : products.findAll()) {
      p.setPrice(p.getPrice().multiply(factor).setScale(2, RoundingMode.HALF_UP));
      products.save(p);
    }
  }
}
