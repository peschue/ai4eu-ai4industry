
async function poll_for_gui_updates() {
  await $.ajax({
    url: 'wait_update?timeout_ms=5000',
    success: function(result) {
      if( result != null ) {
        console.log("got gui update: "+JSON.stringify(result))

        $('#result').html(result.output)
      }
      // schedule this one immediately
      setTimeout(poll_for_gui_updates, 100);
    }
  })
}

$(document).ready(function() {

  $('.itemrb').click(function(ev) {
    // ev.stopPropagation()

    // if we set something to empty, set all items "above" also to empty
    // if we set something to non-empty, reset to empty if item "below" is empty
    let current = $(this).attr('id')
    let pieces = current.split('_')
    let mag = parseInt(pieces[1])
    let itm = parseInt(pieces[2])
    let value = pieces[3]
    // console.log(mag, itm, value, $(this).prop('checked'))

    if( value == 'empty' ) {
      // if we set something to empty, set all items "above" also to empty
      for(let otheritm of [0,1,2]) {
        if( otheritm > itm ) {
          // console.log("setting "+otheritm+" to empty")
          $('#item_' + mag + '_' + otheritm + '_empty')
            .prop('checked', true)
            .change()
        }
      }
    } else if (itm > 0) {
      // if we set something (except the lowest) to non-empty,
      // reset to empty if item "below" is empty
      if( $('#item_' + mag + '_' + (itm-1) + '_empty').prop('checked') ) {
          // console.log("resetting to empty")
          $(this)
          .prop('checked', false)
          .change();
        $('#item_' + mag + '_' + itm + '_empty')
          .prop('checked', true)
          .change()
      }
    }
  })

  $('#submit').click(function(ev) {

    $('#result').html("submitting to pipeline");

    var goal = []
    for(let mag of [0,1,2]) {
      for(let itm of [0,1,2]) {
        for(let col of ['red','blue','white']) {
          if( $('#item_' + mag + '_' + itm + '_' + col).prop('checked') ) {
            goal.push({magazine:mag, item:itm, color:col})
          }
        }
      }
    }
    let payload = {
      magazines: goal,
      maxstep: parseInt($('#maxstep').prop('value')),
    }
    console.log("posting to /goal/ payload "+JSON.stringify(payload))
    $.post(
      'goal',
      JSON.stringify(payload),
      function(data, status) {
        console.log("POST resulted in status "+status)
      }
    )
  })

  setTimeout(poll_for_gui_updates, 1);
});
