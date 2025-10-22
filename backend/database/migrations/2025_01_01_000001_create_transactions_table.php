<?php
use Illuminate\Database\Schema\Blueprint; use Illuminate\Support\Facades\Schema;

return new class {
    public function up(){
        Schema::create('transactions', function(Blueprint $table){
            $table->id();
            $table->foreignId('wallet_id')->constrained()->onDelete('cascade');
            $table->enum('type',['credit','debit']);
            $table->decimal('amount',16,2);
            $table->json('meta')->nullable();
            $table->string('status',32)->default('pending');
            $table->timestamps();
        });
    }
    public function down(){ Schema::dropIfExists('transactions'); }
};
