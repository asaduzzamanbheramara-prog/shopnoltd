<?php
use Illuminate\Database\Schema\Blueprint; use Illuminate\Support\Facades\Schema;

return new class {
    public function up(){
        Schema::create('wallets', function(Blueprint $table){
            $table->id();
            $table->foreignId('user_id')->constrained()->onDelete('cascade');
            $table->string('currency',8)->default('USD');
            $table->decimal('balance',16,2)->default(0);
            $table->timestamps();
        });
    }
    public function down(){ Schema::dropIfExists('wallets'); }
};
