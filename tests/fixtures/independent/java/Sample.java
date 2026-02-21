package com.example;

import java.util.Objects;

public class Sample {
    public Sample() {}

    public void run() {
        Objects.requireNonNull("x");
        helper();
    }

    private void helper() {}
}
