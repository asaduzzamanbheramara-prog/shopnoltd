<?php
namespace App\Services\Payment;

interface PaymentGatewayInterface
{
    public function createPaymentIntent($user, float $amount, string $currency);
    public function handleWebhook(array $payload);
    public function payout($user, float $amount, string $currency);
}
