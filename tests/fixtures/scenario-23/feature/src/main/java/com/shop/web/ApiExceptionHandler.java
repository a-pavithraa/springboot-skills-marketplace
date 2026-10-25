package com.shop.web;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import java.io.*; import java.util.Map;
@RestControllerAdvice
class ApiExceptionHandler {
  @ExceptionHandler(Exception.class)
  ResponseEntity<Map<String,String>> handle(Exception e) {
    StringWriter sw = new StringWriter(); e.printStackTrace(new PrintWriter(sw));
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("error", e.getMessage(), "trace", sw.toString()));
  }
}
