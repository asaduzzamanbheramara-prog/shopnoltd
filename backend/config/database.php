<?php

return [

    // Default database connection
    'default' => env('DB_CONNECTION', 'pgsql'),

    'connections' => [

        'pgsql' => [
            'driver'   => 'pgsql',
            'host'     => env('DB_HOST', 'db'),
            'port'     => env('DB_PORT', '5432'),
            'database' => env('DB_DATABASE', 'shopnoltd'),
            'username' => env('DB_USERNAME', 'shopuser'),
            'password' => env('DB_PASSWORD', 'Asad18081978#'),
            'charset'  => 'utf8',
            'prefix'   => '',
            'schema'   => 'public',
            'sslmode'  => 'prefer',
        ],

    ],

];
