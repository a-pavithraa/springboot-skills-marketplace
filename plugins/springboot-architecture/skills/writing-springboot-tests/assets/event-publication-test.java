package {{PACKAGE}}.orders;

import {{PACKAGE}}.TestcontainersConfiguration;
import com.github.tomakehurst.wiremock.WireMockServer;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.resttestclient.autoconfigure.AutoConfigureRestTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.web.servlet.client.RestTestClient;
import org.wiremock.spring.ConfigureWireMock;
import org.wiremock.spring.EnableWireMock;
import org.wiremock.spring.InjectWireMock;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static com.github.tomakehurst.wiremock.stubbing.Scenario.STARTED;
import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.boot.test.context.SpringBootTest.WebEnvironment.RANDOM_PORT;

/**
 * The event other services rely on: published when the business change commits, and never for a change that
 * rolled back. A unit test that verifies publishEvent() can't see either: the commit is the point.
 *
 * Same annotations as PlaceOrderApiTest, so both share one cached context and one set of containers.
 *
 * The rollback case only proves something if the event is raised BEFORE the step that fails (here: the order
 * announces itself on save, then the charge is declined). If nothing can fail after publishEvent(), publishing
 * inside the transaction is harmless and this test can't tell the difference: check the order of calls first.
 *
 * Proving "not published" without a sleep: the topic has one partition, so after a failed order we place a
 * good one and read up to its event. Anything the failed order published would have arrived before it.
 *
 * With a real transactional outbox or Spring Modulith's event publication registry, test the same two
 * properties, plus: the event row is stored in the same transaction as the order, and an event whose
 * publication failed is sent again (Modulith: IncompleteEventPublications.resubmitIncompletePublications).
 */
@SpringBootTest(webEnvironment = RANDOM_PORT)
@AutoConfigureRestTestClient
@Import(TestcontainersConfiguration.class)
@EnableWireMock(@ConfigureWireMock(name = "payments", baseUrlProperties = "payments.base-url"))
@Sql({"/sql/reset.sql", "/sql/products.sql"})   // products.sql: P-1 "Arc lamp", price 12.50, stock 10
class OrderPlacedPublicationTest {

    static final TopicPartition ORDERS_PLACED = new TopicPartition("orders.placed", 0);

    @Autowired
    RestTestClient client;

    @InjectWireMock("payments")
    WireMockServer payments;

    @Autowired
    ConsumerFactory<?, ?> consumers;

    Consumer<?, ?> events;

    @BeforeEach
    void readOnlyEventsFromThisTest() {
        var overrides = new Properties();
        overrides.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        events = consumers.createConsumer("publication-test", null, null, overrides);
        events.assign(List.of(ORDERS_PLACED));
        events.seekToEnd(List.of(ORDERS_PLACED));
        events.position(ORDERS_PLACED);   // seekToEnd is lazy: resolve it now, before the test sends anything
    }

    @AfterEach
    void close() {
        events.close();
    }

    @Test
    void publishesOrderPlacedWithTheOrderIdAsKey() {
        payments.stubFor(post("/charges").willReturn(okJson("""
                {"chargeId": "ch_1", "status": "CAPTURED"}
                """)));

        String orderId = placeOrder(3);

        var event = awaitEventFor(orderId);
        assertThat(event.value().toString())
                .contains("\"productCode\":\"P-1\"", "\"quantity\":3", "\"total\":37.50");
    }

    @Test
    void publishesNothingForAnOrderThatRolledBack() {
        payments.stubFor(post("/charges").inScenario("one decline").whenScenarioStateIs(STARTED)
                .willReturn(aResponse().withStatus(402)).willSetStateTo("declined"));
        payments.stubFor(post("/charges").inScenario("one decline").whenScenarioStateIs("declined")
                .willReturn(okJson("""
                        {"chargeId": "ch_2", "status": "CAPTURED"}
                        """)));

        client.post().uri("/api/orders").contentType(MediaType.APPLICATION_JSON)
                .body("""
                        {"productCode": "P-1", "quantity": 4}
                        """)
                .exchange().expectStatus().isEqualTo(422);
        String marker = placeOrder(1);

        List<ConsumerRecord<?, ?>> seen = readUpTo(marker);
        assertThat(seen).extracting(r -> r.value().toString()).noneMatch(v -> v.contains("\"quantity\":4"));
    }

    private String placeOrder(int quantity) {
        return client.post().uri("/api/orders").contentType(MediaType.APPLICATION_JSON)
                .body("""
                        {"productCode": "P-1", "quantity": %d}
                        """.formatted(quantity))
                .exchange()
                .expectStatus().isCreated()
                .expectBody(OrderId.class).returnResult().getResponseBody().id();
    }

    record OrderId(String id) {}

    private ConsumerRecord<?, ?> awaitEventFor(String orderId) {
        return readUpTo(orderId).stream().filter(r -> orderId.equals(r.key())).findFirst().orElseThrow();
    }

    private List<ConsumerRecord<?, ?>> readUpTo(String orderId) {
        List<ConsumerRecord<?, ?>> seen = new ArrayList<>();
        await().atMost(Duration.ofSeconds(10)).until(() -> {
            events.poll(Duration.ofMillis(200)).forEach(seen::add);
            return seen.stream().anyMatch(r -> orderId.equals(r.key()));
        });
        return seen;
    }
}
