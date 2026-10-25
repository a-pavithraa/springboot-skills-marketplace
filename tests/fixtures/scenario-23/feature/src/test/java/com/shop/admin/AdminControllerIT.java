package com.shop.admin;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import static org.assertj.core.api.Assertions.assertThat;
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class AdminControllerIT {
  @Autowired TestRestTemplate rest;
  @Test void listRequiresAuth() {
    assertThat(rest.getForEntity("/api/admin/customers", String.class).getStatusCode().value()).isEqualTo(401);
  }
}
