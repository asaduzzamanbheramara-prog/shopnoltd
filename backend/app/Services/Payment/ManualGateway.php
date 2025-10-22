<?php
namespace App\Services\Payment;

class ManualGateway implements PaymentGatewayInterface
{
    public function createPaymentIntent($user, float $amount, string $currency){ return ['provider'=>'manual','status'=>'pending','instructions'=>'Transfer to bank XYZ and send receipt']; }
    public function handleWebhook(array $payload){ return true; }
    public function payout($user, float $amount, string $currency){ return true; }
}
