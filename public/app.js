'use strict';

var app = angular.module('serverapp', ['ui.bootstrap', 'statusService']);

angular.module('statusService', ['ngResource']).
    factory('Data', function ($resource) {
        return $resource('status', {}, {
            query: { method: 'GET', params: {}, isArray: false }
        });
    });

function StatusConroller($scope, $timeout, Data) {
	$scope.data = [];
	$scope.buffer = [];
    (function tick() {
        $scope.buffer = Data.query(function(){
        	$scope.data = $scope.buffer;
            $timeout(tick, 1000);            
        });
    })();
};