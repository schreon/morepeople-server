'use strict';

var app = angular.module('serverapp', ['ui.bootstrap', 'statusService']);

angular.module('statusService', ['ngResource']).
    factory('Data', function ($resource) {
        return $resource('status', {}, {
            query: { method: 'GET', params: {}, isArray: false }
        });
    });

function StatusConroller($scope, $timeout, $http, Data) {

	$scope.mockUsers = [];
	for (var i=0; i < 10; i++) {
		$scope.mockUsers.push(
		{
			'USER_ID':'test_user_'+i,
			'USER_NAME':'Test User '+i,
			'LOC':{
				'LONGITUDE':9.1+0.1*Math.random(),
				'LATITUDE':48.7+0.1*Math.random(),
			},
			'MATCH_TAG':'bier',
			'TIME_LEFT':1000
		}
		);
	}

	$scope.queue = function(user) {
		$http.post("queue", user).then(function(response){
			console.log("queue->response");
			console.log(response.data);
		})
	}


	$scope.accept = function(user) {
		$http.post("accept", user).then(function(response){
			console.log("accept->response");
			console.log(response.data);
		})
	}

	$scope.data = [];
	$scope.buffer = [];
    (function tick() {
        $scope.buffer = Data.query(function(){
        	$scope.data = $scope.buffer;
            $timeout(tick, 1000);            
        });
    })();
};