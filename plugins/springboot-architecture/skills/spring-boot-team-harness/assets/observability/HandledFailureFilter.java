package {{BASE_PACKAGE}};

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.filter.ServerHttpObservationFilter;
import org.springframework.web.servlet.DispatcherServlet;

/**
 * Once an @ExceptionHandler turns an exception into a response, Spring treats it as dealt with: nothing logs it and the
 * observation has no error. This fixes both for every 5xx, so a handler can't hide the cause. A handled 4xx leaves
 * one line with the exception type and no message, which can hold personal data. Handlers only build the response,
 * and shouldn't log the exception again.
 */
@Component
class HandledFailureFilter extends OncePerRequestFilter {

    private static final Logger LOG = LoggerFactory.getLogger(HandledFailureFilter.class);

    /** A Callable or DeferredResult fails on the async dispatch, after the first dispatch has returned. */
    @Override
    protected boolean shouldNotFilterAsyncDispatch() {
        return false;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        chain.doFilter(request, response);
        if (isAsyncStarted(request)) {
            return;
        }
        if (!(request.getAttribute(DispatcherServlet.EXCEPTION_ATTRIBUTE) instanceof Throwable failure)) {
            return;
        }
        int status = response.getStatus();
        if (status >= 500) {
            ServerHttpObservationFilter.findObservationContext(request)
                    .ifPresent(context -> context.setError(failure));
            LOG.error("Request failed with status {}", status, failure);
        } else if (status >= 400) {
            LOG.info("Request answered {} after {}", status, failure.getClass().getSimpleName());
        }
    }
}
