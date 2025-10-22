<?php

return [
    'default' => env('DB_CONNECTION', 'pgsql'),

    'connections' => [
        'mysql' => [
            'driver' => 'mysql',
            'host' => env('DB_HOST','127.0.0.1'),
            'database' => env('DB_DATABASE','superapp_db'),
            'username' => env('DB_USERNAME','root'),
            'password' => env('DB_PASSWORD',''),
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
        ],

        'pgsql' => [
            'driver' => 'pgsql',
            'host' => env('DB_HOST','db'),
            'port' => env('DB_PORT','5432'),
            'database' => env('DB_DATABASE','shopnoltd'),
            'username' => env('DB_USERNAME','shopuser'),
            'password' => env('DB_PASSWORD','Asad18081978#'),
            'charset' => 'utf8',
            'prefix' => '',
            'schema' => 'public',
            'sslmode' => 'prefer',
        ],
    ],
];
