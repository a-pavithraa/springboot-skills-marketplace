package com.shop;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
@SpringBootApplication
@EnableMethodSecurity
public class ShopApplication { public static void main(String[] a){ SpringApplication.run(ShopApplication.class,a);} }
