package com.acme.shop;

import static org.mockito.Mockito.*;

import org.junit.jupiter.api.Test;

class OrderServiceTests {
    @Test
    void listCallsTheRepository() {
        OrderRepository repo = mock(OrderRepository.class);
        new OrderService(repo).list();
        verify(repo).findAll();
    }
}
