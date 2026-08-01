(() => {
  'use strict';
  const config=Object.freeze({
    release:'v4.3.3',
    propertySlug:'arbor-vista-retreat',
    directBookingEnabled:false,
    analyticsEndpoint:'',
    bookingUrl:'https://www.airbnb.com/rooms/1587774879621242014'
  });
  window.ARBOR_RUNTIME_CONFIG=config;
  window.ARBOR_VISTA_CONFIG=config;
})();
