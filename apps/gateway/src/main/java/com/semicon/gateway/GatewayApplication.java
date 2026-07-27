package com.semicon.gateway;

import java.net.URI;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.http.ResponseEntity;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

/**
 * Deliberately small gateway boundary. It preserves method, query string and payload so that
 * browser/API clients use one public origin. OIDC/RBAC policies belong here in production.
 */
@SpringBootApplication
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }

    @Bean
    WebClient analyticsClient(@Value("${analytics.api-url}") String analyticsUrl) {
        return WebClient.builder().baseUrl(analyticsUrl).build();
    }
}

@RestController
class AnalyticsProxy {
    private final WebClient client;

    AnalyticsProxy(WebClient client) {
        this.client = client;
    }

    @RequestMapping("/api/**")
    Mono<ResponseEntity<byte[]>> proxy(ServerHttpRequest request,
                                       @RequestBody(required = false) Mono<byte[]> requestBody) {
        String requestId = request.getHeaders().getFirst("X-Request-ID");
        if (requestId == null || requestId.isBlank()) requestId = UUID.randomUUID().toString();
        final String reqId = requestId;  
        String pathAndQuery = request.getURI().getRawPath()
                + (request.getURI().getRawQuery() == null ? "" : "?" + request.getURI().getRawQuery());
        System.out.println("audit action=api_proxy request_id=" + reqId
                + " method=" + request.getMethod() + " path=" + pathAndQuery);

        WebClient.RequestBodySpec spec = client.method(request.getMethod()).uri(pathAndQuery);
        
        if (request.getMethod() == org.springframework.http.HttpMethod.GET || 
            request.getMethod() == org.springframework.http.HttpMethod.HEAD || 
            request.getMethod() == org.springframework.http.HttpMethod.OPTIONS) {
            return spec.headers(headers -> {
                        headers.addAll(request.getHeaders());
                        headers.set("X-Request-ID", reqId);
                        headers.remove("Host");
                    })
                    .exchangeToMono(response -> response.toEntity(byte[].class));
        } else {
            Mono<byte[]> safeBody = requestBody == null ? Mono.just(new byte[0]) : requestBody.defaultIfEmpty(new byte[0]);
            return spec.headers(headers -> {
                        headers.addAll(request.getHeaders());
                        headers.set("X-Request-ID", reqId);
                        headers.remove("Host");
                    })
                    .body(safeBody, byte[].class)
                    .exchangeToMono(response -> response.toEntity(byte[].class));
        }
    }
}
