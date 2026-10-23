package {{PACKAGE}}.orders.payments;

import {{PACKAGE}}.orders.domain.PaymentGateway;
import com.github.tomakehurst.wiremock.WireMockServer;
import com.github.tomakehurst.wiremock.http.Fault;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.ImportAutoConfiguration;
import org.springframework.boot.http.client.autoconfigure.HttpClientAutoConfiguration;
import org.springframework.boot.http.client.autoconfigure.imperative.ImperativeHttpClientAutoConfiguration;
import org.springframework.boot.restclient.test.autoconfigure.AutoConfigureMockRestServiceServer;
import org.springframework.boot.restclient.test.autoconfigure.RestClientTest;
import org.wiremock.spring.ConfigureWireMock;
import org.wiremock.spring.EnableWireMock;
import org.wiremock.spring.InjectWireMock;

import java.math.BigDecimal;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static com.github.tomakehurst.wiremock.stubbing.Scenario.STARTED;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * An outbound HTTP client against a real HTTP server (WireMock): the request we send, how we read the answer,
 * and every way the other side can fail, as our caller sees it. A mocked PaymentGateway can't show any of this.
 *
 * The slice loads the client, its RestClient.Builder and the @Retryable proxy (from @EnableResilientMethods on
 * the application class). MockRestServiceServer is switched off, because WireMock is the server.
 *
 * Two traps this test caught on Boot 4.1.1 / Framework 7.0.9; both pass silently in a test with a mocked client:
 * - @RestClientTest does not apply spring.http.clients.* (timeouts, client choice): import the two HTTP client
 *   auto-configurations below, or the timeout test sees a client with no timeout at all
 * - @Retryable on a class that implements an interface never retries: the default JDK proxy looks for the
 *   annotation on the interface method. Use @EnableResilientMethods(proxyTargetClass = true)
 *
 * Expected requests come from the provider's API documentation, not from our client code. The cases below are the
 * ones THIS example provider's contract implies. Derive yours from your provider's documentation, clause by clause:
 * units (cents or decimals?), status codes with a special meaning (does 409 mean "already done"?), headers, limits.
 *
 * The slice reads application.properties, so the timeout test runs with the production timeout. Don't shorten it
 * with a test property: a missing or wrong production timeout would then pass.
 */
@RestClientTest(HttpPaymentGateway.class)
@AutoConfigureMockRestServiceServer(enabled = false)
@ImportAutoConfiguration({HttpClientAutoConfiguration.class, ImperativeHttpClientAutoConfiguration.class})
@EnableWireMock(@ConfigureWireMock(name = "payments", baseUrlProperties = "payments.base-url"))
class HttpPaymentGatewayTest {

    @Autowired
    PaymentGateway gateway;   // through the interface the rest of the app uses

    @InjectWireMock("payments")
    WireMockServer payments;

    @Test
    void sendsTheChargeAsTheProviderDocumentsIt() {
        payments.stubFor(post("/charges").willReturn(okJson("""
                {"chargeId": "ch_1", "status": "CAPTURED"}
                """)));

        gateway.charge("O-1", new BigDecimal("37.50"));

        payments.verify(postRequestedFor(urlEqualTo("/charges"))
                .withHeader("Idempotency-Key", equalTo("O-1"))
                .withRequestBody(equalToJson("""
                        {"reference": "O-1", "amount": 37.50}
                        """)));
    }

    @Test
    void aDeclineIsFinalAndIsNotRetried() {
        payments.stubFor(post("/charges").willReturn(aResponse().withStatus(402)));

        assertThatThrownBy(() -> gateway.charge("O-1", new BigDecimal("37.50")))
                .isInstanceOf(PaymentDeclinedException.class)
                .hasMessageContaining("O-1");
        payments.verify(1, postRequestedFor(urlEqualTo("/charges")));   // retrying a decline would be a bug
    }

    @Test
    void retriesAnUnavailableProviderWithTheSameIdempotencyKey() {
        // A WireMock scenario: first call 503, second call 200
        payments.stubFor(post("/charges").inScenario("flaky").whenScenarioStateIs(STARTED)
                .willReturn(aResponse().withStatus(503)).willSetStateTo("recovered"));
        payments.stubFor(post("/charges").inScenario("flaky").whenScenarioStateIs("recovered")
                .willReturn(okJson("""
                        {"chargeId": "ch_1", "status": "CAPTURED"}
                        """)));

        assertThatCode(() -> gateway.charge("O-1", new BigDecimal("37.50"))).doesNotThrowAnyException();

        // Both attempts carry the same key, so the provider charges once even if the first one got through
        payments.verify(2, postRequestedFor(urlEqualTo("/charges")).withHeader("Idempotency-Key", equalTo("O-1")));
    }

    @Test
    void givesUpAfterThreeAttempts() {
        payments.stubFor(post("/charges").willReturn(aResponse().withStatus(500)));

        assertThatThrownBy(() -> gateway.charge("O-1", new BigDecimal("37.50")))
                .isInstanceOf(PaymentUnavailableException.class);
        payments.verify(3, postRequestedFor(urlEqualTo("/charges")));   // 1 call + maxRetries = 2
    }

    @Test
    void aSlowProviderTimesOutInsteadOfHangingTheRequest() {
        // Just past the production read timeout (2 s in application.properties). Without one, the call simply waits
        // and succeeds, and this test fails: that is the bug it guards. ~7 s: 3 attempts x 2 s, the price of the
        // real value.
        payments.stubFor(post("/charges").willReturn(okJson("""
                {"chargeId": "ch_1", "status": "CAPTURED"}
                """).withFixedDelay(2_500)));

        assertThatThrownBy(() -> gateway.charge("O-1", new BigDecimal("37.50")))
                .isInstanceOf(PaymentUnavailableException.class);
    }

    @Test
    void aDroppedConnectionIsUnavailableNotACrash() {
        payments.stubFor(post("/charges").willReturn(aResponse().withFault(Fault.CONNECTION_RESET_BY_PEER)));

        assertThatThrownBy(() -> gateway.charge("O-1", new BigDecimal("37.50")))
                .isInstanceOf(PaymentUnavailableException.class);
    }

    @ParameterizedTest(name = "200 with {0}")
    @ValueSource(strings = {"<html>Gateway maintenance</html>", "{}", "{\"chargeId\": \"ch_1\", \"status\": \"PENDING\"}"})
    void anAnswerThatIsNotACaptureIsNeverTakenAsPaid(String body) {
        // A 200 is not a payment. Cover each way: unreadable, empty, readable but not captured.
        payments.stubFor(post("/charges").willReturn(okJson(body)));

        assertThatThrownBy(() -> gateway.charge("O-1", new BigDecimal("37.50")))
                .isInstanceOf(PaymentUnavailableException.class);
    }
}
