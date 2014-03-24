'use strict';

var app = angular.module('morepeopleFrontend',['geolocation', 'ui.bootstrap'])

function mainCtrl($scope, $timeout, $http, geolocation) {

	/** geo location **/
    geolocation.getLocation().then(function(data){
    	console.log(data.coords);
      	$scope.coords = data.coords;
    });

    /** user widget **/
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

    /** carousel **/
    $scope.slides = [
    	{
    		image : '/img/device-2014-03-23-221607.png',
    		text : '...'
    	},{
    		image : '/img/device-2014-03-23-221733.png',
    		text : '...'
    	},{
    		image : '/img/device-2014-03-23-221816.png',
    		text : '...'
    	},{
    		image : '/img/device-2014-03-23-221832.png',
    		text : '...'
    	},{
    		image : '/img/device-2014-03-23-221851.png',
    		text : '...'
    	},{
    		image : '/img/device-2014-03-23-221906.png',
    		text : '...'
    	},{
    		image : '/img/device-2014-03-23-221917.png',
    		text : '...'
    	},{
    		image : '/img/device-2014-03-23-222027.png',
    		text : '...'
    	},{
    		image : '/img/device-2014-03-23-222050.png',
    		text : '...'
    	},
    ];
}