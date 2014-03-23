'use strict';

var app = angular.module('morepeopleFrontend',['geolocation', 'ui.bootstrap'])

function mainCtrl($scope, $timeout, $http, geolocation) {
    geolocation.getLocation().then(function(data){
    	console.log(data.coords);
      	$scope.coords = data.coords;
    });

    $scope.data = [];
	$scope.buffer = [];
    (function tick() {
    	if($scope.coords != undefined) {	    		
	        $http({ 
        		url : "/queue",
        		method: 'GET',
        		params: {
	            	"LON" : $scope.coords.longitude,
	            	"LAT" : $scope.coords.latitude,
	            	"RAD" : 1000,
	            }
	        })
	        .success(function(data, status, headers, config) {
		      console.log(data.SEARCHENTRIES);
		      $scope.users = data.SEARCHENTRIES;
		    })
    	}
        $timeout(tick, 2000); 
    })();
}