<?php
namespace App\Services\Payment;

class StripeGateway implements PaymentGatewayInterface
{
    public function createPaymentIntent($user, float $amount, string $currency){ return ['provider'=>'stripe','status'=>'created','amount'=>$amount,'currency'=>$currency]; }
    public function handleWebhook(array $payload){ return true; }
    public function payout($user, float $amount, string $currency){ return true; }
}
