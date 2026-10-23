package {{PACKAGE}}.orders;

import {{PACKAGE}}.TestcontainersConfiguration;
import com.github.tomakehurst.wiremock.WireMockServer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.resttestclient.autoconfigure.AutoConfigureRestTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.web.servlet.client.RestTestClient;
import org.wiremock.spring.ConfigureWireMock;
import org.wiremock.spring.EnableWireMock;
import org.wiremock.spring.InjectWireMock;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.boot.test.context.SpringBootTest.WebEnvironment.RANDOM_PORT;

/**
 * Over a real port: the whole service, its real database in a container, real HTTP in and out.
 * Other services (here the payment provider) are WireMock stubs: we own neither their code nor their uptime.
 * In a service that talks to others, most tests look like this; in a monolith, keep a few for critical paths.
 *
 * @Transactional does NOT roll back here: the server commits on its own thread. The @Sql scripts reset the
 * data before each test, so tests don't depend on order. WireMock stubs are reset after each test.
 *
 * Test dependency: org.wiremock.integrations:wiremock-spring-boot (not managed by Boot; 4.4.3 runs on Boot 4.1).
 */
@SpringBootTest(webEnvironment = RANDOM_PORT)
@AutoConfigureRestTestClient
@Import(TestcontainersConfiguration.class)
@EnableWireMock(@ConfigureWireMock(name = "payments", baseUrlProperties = "payments.base-url"))
@Sql({"/sql/reset.sql", "/sql/products.sql"})   // products.sql: P-1 "Arc lamp", price 12.50, stock 10
class PlaceOrderApiTest {

    @Autowired
    RestTestClient client;

    @InjectWireMock("payments")
    WireMockServer payments;

    @Test
    void placesAnOrderChargesItAndReducesTheStock() {
        payments.stubFor(post("/charges").willReturn(okJson("""
                {"chargeId": "ch_1", "status": "CAPTURED"}
                """)));

        String location = client.post().uri("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .body("""
                        {"productCode": "P-1", "quantity": 3}
                        """)
                .exchange()
                .expectStatus().isCreated()
                .expectBody()
                .jsonPath("$.total").isEqualTo(37.50)       // 3 x 12.50 from products.sql
                .jsonPath("$.status").isEqualTo("PLACED")
                .returnResult()
                .getResponseHeaders().getLocation().toString();

        client.get().uri(location)
                .exchange()
                .expectStatus().isOk()
                .expectBody().jsonPath("$.quantity").isEqualTo(3);

        client.get().uri("/api/products/P-1")
                .exchange()
                .expectBody().jsonPath("$.stock").isEqualTo(10 - 3);   // the side effect, seen from outside

        // What went over the wire to the provider, as the provider's API documents it
        payments.verify(postRequestedFor(urlEqualTo("/charges"))
                .withRequestBody(equalToJson("""
                        {"reference": "${json-unit.any-string}", "amount": 37.50}
                        """)));   // numbers compare as numbers: 37.5 matches 37.50
    }

    @Test
    void refusesAnOrderLargerThanTheStockWithoutCharging() {
        client.post().uri("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .body("""
                        {"productCode": "P-1", "quantity": 11}
                        """)
                .exchange()
                .expectStatus().isEqualTo(422)
                .expectBody().jsonPath("$.detail").value(String.class, detail -> assertThat(detail).contains("P-1"));

        client.get().uri("/api/products/P-1")
                .exchange()
                .expectBody().jsonPath("$.stock").isEqualTo(10);
        payments.verify(0, postRequestedFor(urlEqualTo("/charges")));
    }

    @Test
    void aDeclinedPaymentRollsBackTheStockReservation() {
        // The failure only a test with the real database can see: does the whole transaction roll back?
        payments.stubFor(post("/charges").willReturn(aResponse().withStatus(402)));

        client.post().uri("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .body("""
                        {"productCode": "P-1", "quantity": 3}
                        """)
                .exchange()
                .expectStatus().isEqualTo(422);

        client.get().uri("/api/products/P-1")
                .exchange()
                .expectBody().jsonPath("$.stock").isEqualTo(10);
    }
}
