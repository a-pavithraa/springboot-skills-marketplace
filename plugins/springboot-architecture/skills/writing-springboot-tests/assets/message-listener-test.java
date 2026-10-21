package {{PACKAGE}}.catalog.messaging;

import {{PACKAGE}}.TestcontainersConfiguration;
import {{PACKAGE}}.catalog.domain.Product;
import {{PACKAGE}}.catalog.domain.ProductRepository;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.ByteArrayDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.kafka.autoconfigure.KafkaConnectionDetails;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.test.context.jdbc.Sql;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/**
 * A message listener against a real broker and a real database, both in containers (shared
 * TestcontainersConfiguration): message in, state out. Assert the stored state with Awaitility, never a sleep.
 *
 * What the listener must survive, besides the happy path:
 * - the same message delivered twice (Kafka and RabbitMQ deliver at least once)
 * - a message it can't process, or can't even deserialize: it must go to the dead-letter topic, and the next
 *   message must still be handled
 *
 * Messages to one key go to one partition and arrive in order. The tests use that: once a later message with
 * the same key has been applied, the earlier ones have been handled too, so "nothing else happened" is
 * provable without waiting.
 *
 * Needs, in application.properties:
 *   spring.kafka.consumer.auto-offset-reset=earliest   (or a message sent before the listener joins is skipped)
 *   spring.kafka.consumer.value-deserializer=org.springframework.kafka.support.serializer.ErrorHandlingDeserializer
 *   spring.kafka.consumer.properties.spring.deserializer.value.delegate.class=<your JSON deserializer>
 * and a DefaultErrorHandler bean with a DeadLetterPublishingRecoverer.
 */
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@Sql({"/sql/reset.sql", "/sql/products.sql"})   // products.sql: P-1 "Arc lamp", stock 10
class StockDeliveredListenerTest {

    static final String TOPIC = "warehouse.stock-delivered";

    @Autowired
    KafkaTemplate<String, Object> kafka;

    @Autowired
    ProductRepository products;

    @Autowired
    ConsumerFactory<?, ?> consumers;

    @Autowired
    KafkaConnectionDetails broker;   // the container's address, from @ServiceConnection

    String eventId;

    @BeforeEach
    void newEventId() {
        eventId = UUID.randomUUID().toString();   // unique per test: processed ids survive @Sql resets
    }

    @Test
    void addsTheDeliveredQuantityToTheStock() {
        kafka.send(TOPIC, "P-1", new RestockListener.StockDelivered(eventId, "P-1", 5));

        await().atMost(Duration.ofSeconds(10))
                .untilAsserted(() -> assertThat(stockOf("P-1")).isEqualTo(10 + 5));
    }

    @Test
    void appliesARedeliveredEventOnlyOnce() {
        var delivery = new RestockListener.StockDelivered(eventId, "P-1", 5);
        kafka.send(TOPIC, "P-1", delivery);
        kafka.send(TOPIC, "P-1", delivery);                                    // the broker redelivers
        kafka.send(TOPIC, "P-1", new RestockListener.StockDelivered(UUID.randomUUID().toString(), "P-1", 1));

        // When the third (same key, so later) message is applied, both copies of the first have been handled
        await().atMost(Duration.ofSeconds(10))
                .untilAsserted(() -> assertThat(stockOf("P-1")).isEqualTo(10 + 5 + 1));
    }

    @Test
    void sendsAMessageItCannotProcessToTheDeadLetterTopicAndCarriesOn() {
        kafka.send(TOPIC, "P-1", new RestockListener.StockDelivered(eventId, "P-1", 0));     // invalid: quantity 0
        kafka.send(TOPIC, "P-1", new RestockListener.StockDelivered(UUID.randomUUID().toString(), "P-1", 2));

        await().atMost(Duration.ofSeconds(10))
                .untilAsserted(() -> assertThat(stockOf("P-1")).isEqualTo(10 + 2));    // not stuck behind it
        awaitDeadLetterContaining(eventId);
    }

    @Test
    void aMessageThatIsNotJsonDoesNotBlockThePartition() {
        // Without ErrorHandlingDeserializer this record never reaches the listener or the error handler:
        // the consumer fails on it forever and every later message on the partition waits behind it.
        String garbage = "not a delivery " + eventId;
        rawStrings().send(TOPIC, "P-1", garbage);
        kafka.send(TOPIC, "P-1", new RestockListener.StockDelivered(UUID.randomUUID().toString(), "P-1", 2));

        await().atMost(Duration.ofSeconds(10))
                .untilAsserted(() -> assertThat(stockOf("P-1")).isEqualTo(10 + 2));
        awaitDeadLetterContaining(garbage);
    }

    private KafkaTemplate<String, String> rawStrings() {
        Map<String, Object> config = Map.of(
                ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, String.join(",", broker.getBootstrapServers()));
        return new KafkaTemplate<>(new DefaultKafkaProducerFactory<>(config, new StringSerializer(), new StringSerializer()));
    }

    private void awaitDeadLetterContaining(String expected) {
        var overrides = new Properties();
        overrides.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ByteArrayDeserializer.class);
        overrides.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        try (var dlt = consumers.createConsumer("dlt-" + eventId, null, null, overrides)) {
            dlt.subscribe(List.of(TOPIC + "-dlt"));   // Spring Kafka 4 default name: <topic>-dlt
            // Keep polling and collecting: one poll returns one batch, and the record may be in a later one
            List<String> seen = new ArrayList<>();
            await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> {
                dlt.poll(Duration.ofMillis(200)).forEach(r -> seen.add(new String((byte[]) r.value(), StandardCharsets.UTF_8)));
                assertThat(seen).anySatisfy(value -> assertThat(value).contains(expected));
            });
        }
    }

    private int stockOf(String code) {
        return products.findByCode(code).map(Product::getStock).orElseThrow();
    }
}
