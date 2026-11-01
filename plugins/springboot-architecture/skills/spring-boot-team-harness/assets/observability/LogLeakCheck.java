package {{TEST_PACKAGE}};

import static org.assertj.core.api.Assertions.fail;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.classic.spi.IThrowableProxy;
import ch.qos.logback.core.read.ListAppender;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import org.junit.jupiter.api.extension.AfterEachCallback;
import org.junit.jupiter.api.extension.BeforeEachCallback;
import org.junit.jupiter.api.extension.ExtensionContext;
import org.slf4j.LoggerFactory;

/**
 * Runs around every test and fails it when the app's own code logs an email address or a credential. Names, phone
 * numbers and other identifiers have no reliable shape, so REVIEW.md covers those. Framework logs are left out.
 */
public class LogLeakCheck implements BeforeEachCallback, AfterEachCallback {

    private static final String BASE_PACKAGE = "{{BASE_PACKAGE}}";

    private static final ExtensionContext.Namespace NAMESPACE = ExtensionContext.Namespace.create(LogLeakCheck.class);

    private static final Map<String, Pattern> SENSITIVE = Map.of(
            "an email address", Pattern.compile("[\\w.+-]+@[\\w-]+\\.[\\w.-]+"),
            "a JWT", Pattern.compile("eyJ[\\w-]+\\.[\\w-]+\\.[\\w-]+"),
            "a bearer token", Pattern.compile("(?i)bearer\\s+[\\w.~+/-]{8,}"),
            "a credential", Pattern.compile("(?i)(password|passwd|secret|api[_-]?key|token)\\s*[=:]\\s*[^\\s,{}\\[\\]]+"));

    @Override
    public void beforeEach(ExtensionContext context) {
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        root().addAppender(appender);
        context.getStore(NAMESPACE).put("appender", appender);
    }

    @Override
    @SuppressWarnings("unchecked")
    public void afterEach(ExtensionContext context) {
        ListAppender<ILoggingEvent> appender =
                (ListAppender<ILoggingEvent>) context.getStore(NAMESPACE).remove("appender");
        root().detachAppender(appender);
        for (ILoggingEvent event : List.copyOf(appender.list)) {
            if (event.getLoggerName().startsWith(BASE_PACKAGE)) {
                check(event);
            }
        }
    }

    private static void check(ILoggingEvent event) {
        String text = text(event);
        SENSITIVE.forEach((kind, pattern) -> {
            if (pattern.matcher(text).find()) {
                fail("%s logged %s. Log an internal id instead, or give the type a toString that leaves the value "
                        + "out. Logs are exported as they are: %s", event.getLoggerName(), kind,
                        event.getMessage());
            }
        });
    }

    private static String text(ILoggingEvent event) {
        StringBuilder text = new StringBuilder(event.getFormattedMessage());
        if (event.getKeyValuePairs() != null) {
            event.getKeyValuePairs().forEach(pair -> text.append(' ').append(pair.key).append('=').append(pair.value));
        }
        for (IThrowableProxy cause = event.getThrowableProxy(); cause != null; cause = cause.getCause()) {
            text.append(' ').append(cause.getMessage());
        }
        return text.toString();
    }

    private static Logger root() {
        return (Logger) LoggerFactory.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME);
    }
}
